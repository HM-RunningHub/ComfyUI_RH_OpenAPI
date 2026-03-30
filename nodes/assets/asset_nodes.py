"""
SparkVideo asset management nodes.
"""

import json
import math
import os
import re
import shutil
import subprocess
import tempfile
import time
from fractions import Fraction
from io import BytesIO

import torch
from PIL import Image

from ...core.audio import audio_to_bytes
from ...core.image import tensor_to_pil
from ...core.rest import dumps_json, post_json
from ...core.upload import upload_file
from .base import AssetRestNodeBase, clean_string, connectable_string_input, text_input


FIXED_ASSET_GROUP_ID = "group-20260327004931-dvjbj"
FIXED_ASSET_NAME = "RHas01"
ASSET_READY_STATUSES = {"ACTIVE", "SUCCESS", "SUCCEEDED", "COMPLETED", "DONE", "READY", "AVAILABLE"}
ASSET_FAILED_STATUSES = {"FAILED", "ERROR", "CANCEL", "CANCELED"}
ASSET_READY_TIMEOUTS = {
    "image": 60,
    "video": 180,
    "audio": 60,
}
VOLC_VIDEO_MIN_DURATION_SECONDS = 2.0
VOLC_VIDEO_MAX_DURATION_SECONDS = 15.0
VOLC_VIDEO_MIN_RATIO = 0.4
VOLC_VIDEO_MAX_RATIO = 2.5
VOLC_VIDEO_MIN_DIMENSION = 300
VOLC_VIDEO_MAX_DIMENSION = 6000
VOLC_VIDEO_MIN_PIXELS = 640 * 640
VOLC_VIDEO_MAX_PIXELS = 834 * 1112
VOLC_VIDEO_MIN_FPS = 24.0
VOLC_VIDEO_MAX_FPS = 60.0
VOLC_VIDEO_MAX_SIZE_BYTES = 50 * 1024 * 1024
VOLC_VIDEO_AUDIO_BITRATE_KBPS = 128
VOLC_VIDEO_DEFAULT_FPS = 30.0
VOLC_VIDEO_FFPROBE_TIMEOUT_SECONDS = 60
VOLC_VIDEO_FFMPEG_TIMEOUT_SECONDS = 300
VOLC_AUDIO_MIN_DURATION_SECONDS = 2.0
VOLC_AUDIO_MAX_DURATION_SECONDS = 15.0
VOLC_AUDIO_MAX_SIZE_BYTES = 15 * 1024 * 1024
VOLC_AUDIO_MAX_SAMPLE_RATE = 48000
VOLC_IMAGE_MIN_RATIO = 0.4
VOLC_IMAGE_MAX_RATIO = 2.5
VOLC_IMAGE_MIN_DIMENSION = 300
VOLC_IMAGE_MAX_DIMENSION = 6000
VOLC_IMAGE_MAX_SIZE_BYTES = 10 * 1024 * 1024
VOLC_IMAGE_TARGET_FORMAT = "JPEG"


def _log_video_asset(logger_prefix: str, message: str):
    print(f"[{logger_prefix}] {message}")


def _log_audio_asset(logger_prefix: str, message: str):
    print(f"[{logger_prefix}] {message}")


def _log_image_asset(logger_prefix: str, message: str):
    print(f"[{logger_prefix}] {message}")


def _format_size_mb(size_bytes: int) -> str:
    return f"{float(size_bytes or 0) / (1024 * 1024):.2f}MB"


def _describe_video_info(info: dict) -> str:
    width = int(info.get("width") or 0)
    height = int(info.get("height") or 0)
    duration = float(info.get("duration") or 0.0)
    fps = float(info.get("fps") or 0.0)
    size_bytes = int(info.get("size_bytes") or 0)
    format_name = str(info.get("format_name") or "unknown")
    audio = "yes" if info.get("has_audio") else "no"
    return (
        f"format={format_name}, "
        f"resolution={width}x{height}, "
        f"duration={duration:.2f}s, "
        f"fps={fps:.2f}, "
        f"size={_format_size_mb(size_bytes)}, "
        f"audio={audio}"
    )


def _normalize_audio_waveform(audio_dict) -> tuple[torch.Tensor, int]:
    if not isinstance(audio_dict, dict) or "waveform" not in audio_dict or "sample_rate" not in audio_dict:
        raise ValueError("audio input must be a valid ComfyUI AUDIO value")

    waveform = audio_dict["waveform"]
    sample_rate = int(audio_dict["sample_rate"])
    if sample_rate <= 0:
        raise ValueError(f"Invalid audio sample_rate: {sample_rate}")

    if not isinstance(waveform, torch.Tensor):
        raise ValueError("audio waveform must be a torch.Tensor")

    waveform = waveform.detach().cpu().float()
    if waveform.dim() == 3:
        waveform = waveform.squeeze(0)
    if waveform.dim() == 1:
        waveform = waveform.unsqueeze(0)
    if waveform.dim() != 2:
        raise ValueError(f"Unsupported audio waveform shape: {tuple(waveform.shape)}")
    if waveform.shape[-1] <= 0:
        raise ValueError("audio waveform has no samples")

    waveform = torch.nan_to_num(waveform, nan=0.0, posinf=1.0, neginf=-1.0)
    waveform = waveform.clamp(-1.0, 1.0).contiguous()
    return waveform, sample_rate


def _build_audio_info(waveform: torch.Tensor, sample_rate: int, file_size_bytes: int = 0) -> dict:
    channels = int(waveform.shape[0]) if waveform.dim() >= 2 else 1
    samples = int(waveform.shape[-1]) if waveform.dim() >= 1 else 0
    duration = float(samples) / float(sample_rate) if sample_rate > 0 and samples > 0 else 0.0
    return {
        "channels": channels,
        "samples": samples,
        "sample_rate": int(sample_rate),
        "duration": duration,
        "size_bytes": int(file_size_bytes or 0),
    }


def _describe_audio_info(info: dict) -> str:
    return (
        f"channels={int(info.get('channels') or 0)}, "
        f"sample_rate={int(info.get('sample_rate') or 0)}Hz, "
        f"samples={int(info.get('samples') or 0)}, "
        f"duration={float(info.get('duration') or 0.0):.2f}s, "
        f"size={_format_size_mb(int(info.get('size_bytes') or 0))}"
    )


def _build_image_info(image: Image.Image, file_size_bytes: int = 0, format_name: str = "") -> dict:
    width = int(image.width or 0)
    height = int(image.height or 0)
    ratio = float(width) / float(height) if width > 0 and height > 0 else 0.0
    return {
        "width": width,
        "height": height,
        "ratio": ratio,
        "mode": str(image.mode or ""),
        "size_bytes": int(file_size_bytes or 0),
        "format_name": str(format_name or ""),
    }


def _describe_image_info(info: dict) -> str:
    return (
        f"format={str(info.get('format_name') or 'unknown')}, "
        f"resolution={int(info.get('width') or 0)}x{int(info.get('height') or 0)}, "
        f"ratio={float(info.get('ratio') or 0.0):.4f}, "
        f"mode={str(info.get('mode') or 'unknown')}, "
        f"size={_format_size_mb(int(info.get('size_bytes') or 0))}"
    )


def _validate_preprocessed_image_info(info: dict):
    errors = []
    width = int(info.get("width") or 0)
    height = int(info.get("height") or 0)
    ratio = float(info.get("ratio") or 0.0)
    size_bytes = int(info.get("size_bytes") or 0)

    if width < VOLC_IMAGE_MIN_DIMENSION or width > VOLC_IMAGE_MAX_DIMENSION:
        errors.append(f"width={width}")
    if height < VOLC_IMAGE_MIN_DIMENSION or height > VOLC_IMAGE_MAX_DIMENSION:
        errors.append(f"height={height}")
    if ratio < VOLC_IMAGE_MIN_RATIO or ratio > VOLC_IMAGE_MAX_RATIO:
        errors.append(f"ratio={ratio:.4f}")
    if size_bytes > VOLC_IMAGE_MAX_SIZE_BYTES:
        errors.append(f"size={_format_size_mb(size_bytes)}")

    if errors:
        raise RuntimeError(
            "Preprocessed image still does not meet Volc asset requirements: "
            + ", ".join(errors)
        )


def _image_has_alpha(image: Image.Image) -> bool:
    if image.mode in {"RGBA", "LA"}:
        return True
    return image.mode == "P" and "transparency" in image.info


def _normalize_image_mode(image: Image.Image) -> Image.Image:
    if _image_has_alpha(image):
        rgba_image = image.convert("RGBA")
        background = Image.new("RGBA", rgba_image.size, (255, 255, 255, 255))
        composited = Image.alpha_composite(background, rgba_image)
        return composited.convert("RGB")
    if image.mode != "RGB":
        return image.convert("RGB")
    return image


def _crop_image_to_ratio_bounds(image: Image.Image) -> tuple[Image.Image, str]:
    width = int(image.width or 0)
    height = int(image.height or 0)
    if width <= 0 or height <= 0:
        raise RuntimeError("Image has invalid dimensions")

    ratio = float(width) / float(height)
    if ratio > VOLC_IMAGE_MAX_RATIO:
        target_width = max(1, int(round(height * VOLC_IMAGE_MAX_RATIO)))
        left = max(0, (width - target_width) // 2)
        right = min(width, left + target_width)
        return image.crop((left, 0, right, height)), f"crop=center width {width} -> {right - left}"

    if ratio < VOLC_IMAGE_MIN_RATIO:
        target_height = max(1, int(round(width / VOLC_IMAGE_MIN_RATIO)))
        top = max(0, (height - target_height) // 2)
        bottom = min(height, top + target_height)
        return image.crop((0, top, width, bottom)), f"crop=center height {height} -> {bottom - top}"

    return image, "crop=keep"


def _resize_image_to_dimension_bounds(image: Image.Image) -> tuple[Image.Image, str]:
    width = int(image.width or 0)
    height = int(image.height or 0)
    min_dimension = min(width, height)
    max_dimension = max(width, height)

    if min_dimension <= 0 or max_dimension <= 0:
        raise RuntimeError("Image has invalid dimensions")

    scale = 1.0
    if min_dimension < VOLC_IMAGE_MIN_DIMENSION:
        scale = float(VOLC_IMAGE_MIN_DIMENSION) / float(min_dimension)
    elif max_dimension > VOLC_IMAGE_MAX_DIMENSION:
        scale = float(VOLC_IMAGE_MAX_DIMENSION) / float(max_dimension)

    if abs(scale - 1.0) < 1e-6:
        return image, "scale=keep"

    new_width = max(VOLC_IMAGE_MIN_DIMENSION, min(VOLC_IMAGE_MAX_DIMENSION, int(round(width * scale))))
    new_height = max(VOLC_IMAGE_MIN_DIMENSION, min(VOLC_IMAGE_MAX_DIMENSION, int(round(height * scale))))
    resized = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
    return resized, f"scale={width}x{height} -> {new_width}x{new_height}"


def _encode_image_bytes(image: Image.Image) -> tuple[bytes, str, str]:
    if image.mode != "RGB":
        image = image.convert("RGB")

    best_result = None
    working_image = image
    qualities = (95, 90, 85, 80, 75, 70, 65, 60)

    for _attempt in range(6):
        for quality in qualities:
            buffer = BytesIO()
            working_image.save(
                buffer,
                format=VOLC_IMAGE_TARGET_FORMAT,
                quality=quality,
                optimize=True,
                progressive=True,
            )
            payload = buffer.getvalue()
            result = (payload, VOLC_IMAGE_TARGET_FORMAT, "image/jpeg")
            if len(payload) <= VOLC_IMAGE_MAX_SIZE_BYTES:
                return result
            if best_result is None or len(payload) < len(best_result[0]):
                best_result = result

        width = int(working_image.width or 0)
        height = int(working_image.height or 0)
        if width <= VOLC_IMAGE_MIN_DIMENSION and height <= VOLC_IMAGE_MIN_DIMENSION:
            break

        next_width = max(VOLC_IMAGE_MIN_DIMENSION, int(round(width * 0.9)))
        next_height = max(VOLC_IMAGE_MIN_DIMENSION, int(round(height * 0.9)))
        if next_width == width and next_height == height:
            break
        working_image = working_image.resize((next_width, next_height), Image.Resampling.LANCZOS)

    if best_result is None:
        raise RuntimeError("Failed to encode image")
    return best_result


def preprocess_image_for_volc_asset(media_value, logger_prefix: str) -> dict:
    """Normalize arbitrary IMAGE input into a Volc-compatible image asset."""
    images = tensor_to_pil(media_value)
    if not images:
        raise ValueError("image input must contain at least one frame")

    processed_image = _normalize_image_mode(images[0])
    original_info = _build_image_info(processed_image, format_name=processed_image.mode)

    _log_image_asset(logger_prefix, "Image asset preprocessing started")
    _log_image_asset(
        logger_prefix,
        f"Original image info: {_describe_image_info(original_info)}",
    )

    processed_image, crop_action = _crop_image_to_ratio_bounds(processed_image)
    processed_image, scale_action = _resize_image_to_dimension_bounds(processed_image)
    _log_image_asset(
        logger_prefix,
        f"Normalization plan: {crop_action}, {scale_action}",
    )

    file_bytes, format_name, mime_type = _encode_image_bytes(processed_image)
    final_info = _build_image_info(processed_image, len(file_bytes), format_name)
    _validate_preprocessed_image_info(final_info)
    _log_image_asset(logger_prefix, "Validation passed; image asset is ready for RH upload")
    _log_image_asset(
        logger_prefix,
        f"Final image info: {_describe_image_info(final_info)}",
    )

    extension = {
        "PNG": ".png",
        "JPEG": ".jpg",
        "WEBP": ".webp",
    }.get(format_name.upper(), ".png")
    return {
        "file_bytes": file_bytes,
        "filename": f"asset_{abs(hash(file_bytes)) % 10**10}{extension}",
        "mime_type": mime_type,
    }


def _resample_audio_waveform(waveform: torch.Tensor, source_rate: int, target_rate: int) -> torch.Tensor:
    if source_rate == target_rate:
        return waveform

    if target_rate <= 0:
        raise ValueError(f"Invalid target audio sample_rate: {target_rate}")

    try:
        import torchaudio.functional as torchaudio_functional

        return torchaudio_functional.resample(waveform, source_rate, target_rate)
    except Exception:
        target_samples = max(
            1,
            int(round(float(waveform.shape[-1]) * float(target_rate) / float(source_rate))),
        )
        resampled = torch.nn.functional.interpolate(
            waveform.unsqueeze(0),
            size=target_samples,
            mode="linear",
            align_corners=False,
        )
        return resampled.squeeze(0)


def _summarize_audio_plan(
    original_info: dict,
    target_channels: int,
    target_sample_rate: int,
    target_duration: float,
) -> str:
    changes = []

    original_channels = int(original_info["channels"])
    if original_channels != target_channels:
        changes.append(f"channels=mix {original_channels} -> {target_channels}")
    else:
        changes.append(f"channels=keep {target_channels}")

    original_sample_rate = int(original_info["sample_rate"])
    if original_sample_rate != target_sample_rate:
        changes.append(f"sample_rate=resample {original_sample_rate} -> {target_sample_rate}")
    else:
        changes.append(f"sample_rate=keep {target_sample_rate}")

    original_duration = float(original_info["duration"])
    if original_duration < VOLC_AUDIO_MIN_DURATION_SECONDS:
        changes.append(f"duration=pad {original_duration:.2f}s -> {target_duration:.2f}s")
    elif original_duration > VOLC_AUDIO_MAX_DURATION_SECONDS:
        changes.append(f"duration=trim {original_duration:.2f}s -> {target_duration:.2f}s")
    else:
        changes.append(f"duration=keep {target_duration:.2f}s")

    changes.append("format=wav")
    return ", ".join(changes)


def _validate_preprocessed_audio_info(info: dict):
    errors = []
    duration = float(info.get("duration") or 0.0)
    size_bytes = int(info.get("size_bytes") or 0)
    sample_rate = int(info.get("sample_rate") or 0)
    channels = int(info.get("channels") or 0)

    if duration < VOLC_AUDIO_MIN_DURATION_SECONDS - 0.05 or duration > VOLC_AUDIO_MAX_DURATION_SECONDS + 0.05:
        errors.append(f"duration={duration:.3f}s")
    if size_bytes > VOLC_AUDIO_MAX_SIZE_BYTES:
        errors.append(f"size={_format_size_mb(size_bytes)}")
    if sample_rate <= 0:
        errors.append(f"sample_rate={sample_rate}")
    if channels <= 0:
        errors.append(f"channels={channels}")

    if errors:
        raise RuntimeError(
            "Preprocessed audio still does not meet Volc asset requirements: "
            + ", ".join(errors)
        )


def preprocess_audio_for_volc_asset(media_value, logger_prefix: str) -> dict:
    """Normalize arbitrary AUDIO input into a Volc-compatible WAV asset."""
    try:
        waveform, sample_rate = _normalize_audio_waveform(media_value)
        original_info = _build_audio_info(waveform, sample_rate)

        target_channels = int(waveform.shape[0])
        if target_channels > 2:
            target_channels = 1

        target_sample_rate = min(sample_rate, VOLC_AUDIO_MAX_SAMPLE_RATE)
        target_duration = max(
            VOLC_AUDIO_MIN_DURATION_SECONDS,
            min(VOLC_AUDIO_MAX_DURATION_SECONDS, original_info["duration"]),
        )

        _log_audio_asset(logger_prefix, "Audio asset preprocessing started")
        _log_audio_asset(
            logger_prefix,
            f"Original audio info: {_describe_audio_info(original_info)}",
        )
        _log_audio_asset(
            logger_prefix,
            "Normalization plan: "
            + _summarize_audio_plan(original_info, target_channels, target_sample_rate, target_duration),
        )

        processed_waveform = waveform
        if processed_waveform.shape[0] > target_channels:
            processed_waveform = processed_waveform.mean(dim=0, keepdim=True)
            _log_audio_asset(
                logger_prefix,
                f"Downmixed audio to {target_channels} channel(s)",
            )

        if target_sample_rate != sample_rate:
            processed_waveform = _resample_audio_waveform(processed_waveform, sample_rate, target_sample_rate)
            _log_audio_asset(
                logger_prefix,
                f"Resampled audio from {sample_rate}Hz to {target_sample_rate}Hz",
            )

        current_samples = int(processed_waveform.shape[-1])
        current_duration = float(current_samples) / float(target_sample_rate)

        if current_duration > VOLC_AUDIO_MAX_DURATION_SECONDS:
            max_samples = int(round(VOLC_AUDIO_MAX_DURATION_SECONDS * target_sample_rate))
            processed_waveform = processed_waveform[:, :max_samples]
            _log_audio_asset(
                logger_prefix,
                f"Trimmed audio from {current_duration:.2f}s to {VOLC_AUDIO_MAX_DURATION_SECONDS:.2f}s",
            )
        elif current_duration < VOLC_AUDIO_MIN_DURATION_SECONDS:
            target_samples = int(round(VOLC_AUDIO_MIN_DURATION_SECONDS * target_sample_rate))
            padding = target_samples - current_samples
            processed_waveform = torch.nn.functional.pad(processed_waveform, (0, padding))
            _log_audio_asset(
                logger_prefix,
                f"Padded audio from {current_duration:.2f}s to {VOLC_AUDIO_MIN_DURATION_SECONDS:.2f}s",
            )

        processed_waveform = processed_waveform.clamp(-1.0, 1.0).contiguous()
        processed_audio = {
            "waveform": processed_waveform.unsqueeze(0),
            "sample_rate": int(target_sample_rate),
        }

        file_bytes = audio_to_bytes(processed_audio, format="wav")
        output_info = _build_audio_info(processed_waveform, target_sample_rate, len(file_bytes))
        _log_audio_asset(
            logger_prefix,
            f"Pass 1 output info: {_describe_audio_info(output_info)}",
        )

        if len(file_bytes) > VOLC_AUDIO_MAX_SIZE_BYTES and processed_waveform.shape[0] > 1:
            _log_audio_asset(
                logger_prefix,
                "Pass 1 output exceeds 15MB; retrying with mono mixdown",
            )
            mono_waveform = processed_waveform.mean(dim=0, keepdim=True).contiguous()
            mono_audio = {
                "waveform": mono_waveform.unsqueeze(0),
                "sample_rate": int(target_sample_rate),
            }
            file_bytes = audio_to_bytes(mono_audio, format="wav")
            processed_waveform = mono_waveform
            output_info = _build_audio_info(processed_waveform, target_sample_rate, len(file_bytes))
            _log_audio_asset(
                logger_prefix,
                f"Pass 2 output info: {_describe_audio_info(output_info)}",
            )

        if len(file_bytes) > VOLC_AUDIO_MAX_SIZE_BYTES:
            current_waveform = processed_waveform
            current_rate = int(target_sample_rate)
            for fallback_rate in (32000, 24000, 16000):
                if current_rate <= fallback_rate:
                    continue
                _log_audio_asset(
                    logger_prefix,
                    f"Output still exceeds 15MB; retrying with {fallback_rate}Hz resample",
                )
                current_waveform = _resample_audio_waveform(processed_waveform, target_sample_rate, fallback_rate)
                current_rate = fallback_rate
                fallback_audio = {
                    "waveform": current_waveform.unsqueeze(0),
                    "sample_rate": current_rate,
                }
                file_bytes = audio_to_bytes(fallback_audio, format="wav")
                output_info = _build_audio_info(current_waveform, current_rate, len(file_bytes))
                _log_audio_asset(
                    logger_prefix,
                    f"Fallback output info: {_describe_audio_info(output_info)}",
                )
                processed_waveform = current_waveform
                target_sample_rate = current_rate
                if len(file_bytes) <= VOLC_AUDIO_MAX_SIZE_BYTES:
                    break

        final_info = _build_audio_info(processed_waveform, target_sample_rate, len(file_bytes))
        _validate_preprocessed_audio_info(final_info)
        _log_audio_asset(logger_prefix, "Validation passed; audio asset is ready for RH upload")
        _log_audio_asset(
            logger_prefix,
            f"Final audio info: {_describe_audio_info(final_info)}",
        )

        return {
            "file_bytes": file_bytes,
            "filename": f"asset_{abs(hash(file_bytes)) % 10**10}.wav",
            "mime_type": "audio/wav",
        }
    except Exception as e:
        _log_audio_asset(logger_prefix, f"ERROR: audio asset preprocessing failed: {e}")
        raise


def _video_to_bytes(value) -> bytes:
    if hasattr(value, "get_stream_source"):
        source = value.get_stream_source()
        if isinstance(source, str) and os.path.isfile(source):
            with open(source, "rb") as f:
                return f.read()
        if hasattr(source, "read"):
            return source.read()

    if hasattr(value, "path") and os.path.isfile(value.path):
        with open(value.path, "rb") as f:
            return f.read()

    if hasattr(value, "file_path") and os.path.isfile(value.file_path):
        with open(value.file_path, "rb") as f:
            return f.read()

    if isinstance(value, dict):
        file_path = value.get("file_path") or value.get("path")
        if file_path and os.path.isfile(file_path):
            with open(file_path, "rb") as f:
                return f.read()

    if isinstance(value, str) and os.path.isfile(value):
        with open(value, "rb") as f:
            return f.read()

    raise ValueError(f"Could not extract video bytes from {type(value).__name__}")


def _extract_video_path(value) -> str:
    if value is None:
        return ""

    if hasattr(value, "get_stream_source"):
        source = value.get_stream_source()
        if isinstance(source, str) and os.path.isfile(source):
            return source

    for attr_name in ("path", "file_path", "filename"):
        path_value = getattr(value, attr_name, None)
        if isinstance(path_value, str) and os.path.isfile(path_value):
            return path_value

    if isinstance(value, dict):
        for key in ("file_path", "path", "filename", "file", "video_path"):
            path_value = value.get(key)
            if isinstance(path_value, str) and os.path.isfile(path_value):
                return path_value

    if isinstance(value, (list, tuple)) and value:
        first_item = value[0]
        if isinstance(first_item, str) and os.path.isfile(first_item):
            return first_item
        if isinstance(first_item, dict):
            for key in ("file_path", "path", "filename", "file", "video_path"):
                path_value = first_item.get(key)
                if isinstance(path_value, str) and os.path.isfile(path_value):
                    return path_value

    if isinstance(value, str) and os.path.isfile(value):
        return value

    return ""


def _materialize_video_input(value) -> tuple[str, bool]:
    video_path = _extract_video_path(value)
    if video_path:
        return video_path, False

    video_bytes = _video_to_bytes(value)
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".bin")
    try:
        temp_file.write(video_bytes)
    finally:
        temp_file.close()
    return temp_file.name, True


def _require_video_tool(tool_name: str):
    if not shutil.which(tool_name):
        raise RuntimeError(
            f"{tool_name} is required to preprocess VIDEO assets. "
            f"Please install {tool_name} in the ComfyUI runtime environment."
        )


def _parse_ffprobe_rate(raw_value) -> float:
    text = str(raw_value or "").strip()
    if not text or text in {"0/0", "N/A"}:
        return 0.0
    try:
        if "/" in text:
            return float(Fraction(text))
        return float(text)
    except (TypeError, ValueError, ZeroDivisionError):
        return 0.0


def _get_video_rotation_degrees(stream: dict) -> int:
    tags = stream.get("tags") or {}
    raw_rotation = tags.get("rotate")
    if raw_rotation not in (None, ""):
        try:
            return int(float(raw_rotation))
        except (TypeError, ValueError):
            pass

    for side_data in stream.get("side_data_list") or []:
        raw_rotation = side_data.get("rotation")
        if raw_rotation not in (None, ""):
            try:
                return int(float(raw_rotation))
            except (TypeError, ValueError):
                continue

    return 0


def _probe_video_info(path: str) -> dict:
    _require_video_tool("ffprobe")

    probe_cmd = [
        "ffprobe",
        "-v",
        "error",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        path,
    ]
    try:
        result = subprocess.run(
            probe_cmd,
            capture_output=True,
            text=True,
            timeout=VOLC_VIDEO_FFPROBE_TIMEOUT_SECONDS,
            check=True,
        )
    except subprocess.TimeoutExpired as e:
        raise RuntimeError(f"ffprobe timed out while reading video metadata: {path}") from e
    except subprocess.CalledProcessError as e:
        stderr = (e.stderr or "").strip()
        raise RuntimeError(f"ffprobe failed to read video metadata: {stderr or path}") from e

    try:
        payload = json.loads(result.stdout or "{}")
    except ValueError as e:
        raise RuntimeError("ffprobe returned invalid JSON while reading video metadata") from e

    streams = payload.get("streams") or []
    format_info = payload.get("format") or {}
    video_stream = next((stream for stream in streams if stream.get("codec_type") == "video"), None)
    if not video_stream:
        raise RuntimeError("No video stream found in the provided VIDEO input")

    width = int(video_stream.get("width") or 0)
    height = int(video_stream.get("height") or 0)
    if width <= 0 or height <= 0:
        raise RuntimeError("Could not determine video dimensions from ffprobe")

    rotation = _get_video_rotation_degrees(video_stream)
    if abs(rotation) % 180 == 90:
        width, height = height, width

    duration = 0.0
    for raw_duration in (
        format_info.get("duration"),
        video_stream.get("duration"),
        video_stream.get("tags", {}).get("DURATION"),
    ):
        try:
            if raw_duration not in (None, ""):
                duration = float(raw_duration)
                break
        except (TypeError, ValueError):
            continue

    size_bytes = 0
    for raw_size in (format_info.get("size"),):
        try:
            if raw_size not in (None, ""):
                size_bytes = int(raw_size)
                break
        except (TypeError, ValueError):
            continue
    if size_bytes <= 0 and os.path.isfile(path):
        size_bytes = os.path.getsize(path)

    fps = _parse_ffprobe_rate(
        video_stream.get("avg_frame_rate") or video_stream.get("r_frame_rate")
    )

    return {
        "format_name": str(format_info.get("format_name") or ""),
        "width": width,
        "height": height,
        "duration": duration,
        "size_bytes": size_bytes,
        "fps": fps,
        "has_audio": any(stream.get("codec_type") == "audio" for stream in streams),
    }


def _clamp_number(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def _clamp_even(value: float, minimum: int, maximum: int) -> int:
    minimum = int(minimum)
    maximum = int(maximum)
    if minimum % 2 != 0:
        minimum += 1
    if maximum % 2 != 0:
        maximum -= 1

    value = int(round(value))
    value = max(minimum, min(maximum, value))
    if value % 2 != 0:
        if value < maximum:
            value += 1
        else:
            value -= 1
    return max(minimum, min(maximum, value))


def _find_best_scaled_dimensions(ratio: float, target_area: float) -> tuple[int, int]:
    min_even = VOLC_VIDEO_MIN_DIMENSION + (VOLC_VIDEO_MIN_DIMENSION % 2)
    max_even = VOLC_VIDEO_MAX_DIMENSION - (VOLC_VIDEO_MAX_DIMENSION % 2)
    ideal_width = math.sqrt(float(target_area) * float(ratio))
    best_candidate = None
    best_score = None

    for width in range(min_even, max_even + 1, 2):
        height = int(round(width / float(ratio)))
        if height % 2 != 0:
            height += 1
        if height < min_even or height > max_even:
            continue

        actual_ratio = float(width) / float(height)
        if actual_ratio < VOLC_VIDEO_MIN_RATIO or actual_ratio > VOLC_VIDEO_MAX_RATIO:
            continue

        area = width * height
        if area < VOLC_VIDEO_MIN_PIXELS or area > VOLC_VIDEO_MAX_PIXELS:
            continue

        score = (
            abs(area - target_area),
            abs(actual_ratio - ratio),
            abs(width - ideal_width),
        )
        if best_score is None or score < best_score:
            best_score = score
            best_candidate = (width, height)

    if best_candidate is None:
        raise RuntimeError(
            f"Could not derive a valid target resolution for ratio={ratio:.4f}"
        )
    return best_candidate


def _compute_volc_video_geometry(width: int, height: int) -> dict:
    crop_width = int(width)
    crop_height = int(height)
    ratio = float(crop_width) / float(crop_height)

    if ratio > VOLC_VIDEO_MAX_RATIO:
        crop_width = _clamp_even(crop_height * VOLC_VIDEO_MAX_RATIO, 2, crop_width)
    elif ratio < VOLC_VIDEO_MIN_RATIO:
        crop_height = _clamp_even(crop_width / VOLC_VIDEO_MIN_RATIO, 2, crop_height)

    crop_x = max(0, (width - crop_width) // 2)
    crop_y = max(0, (height - crop_height) // 2)

    crop_pixels = max(1, crop_width * crop_height)
    target_pixels = _clamp_number(
        float(crop_pixels),
        float(VOLC_VIDEO_MIN_PIXELS),
        float(VOLC_VIDEO_MAX_PIXELS),
    )
    scale_width, scale_height = _find_best_scaled_dimensions(
        float(crop_width) / float(crop_height),
        target_pixels,
    )

    return {
        "crop_width": crop_width,
        "crop_height": crop_height,
        "crop_x": crop_x,
        "crop_y": crop_y,
        "scale_width": scale_width,
        "scale_height": scale_height,
    }


def _format_fps_value(value: float) -> str:
    rounded = round(float(value), 3)
    if abs(rounded - int(round(rounded))) < 0.001:
        return str(int(round(rounded)))
    return f"{rounded:.3f}"


def _build_volc_video_filters(input_info: dict, geometry: dict, target_fps: float) -> str:
    filters = []

    if (
        geometry["crop_width"] != input_info["width"]
        or geometry["crop_height"] != input_info["height"]
        or geometry["crop_x"] != 0
        or geometry["crop_y"] != 0
    ):
        filters.append(
            "crop="
            f"{geometry['crop_width']}:{geometry['crop_height']}:"
            f"{geometry['crop_x']}:{geometry['crop_y']}"
        )

    filters.append(
        f"scale={geometry['scale_width']}:{geometry['scale_height']}:flags=lanczos"
    )
    filters.append(f"fps={_format_fps_value(target_fps)}")

    if input_info["duration"] < VOLC_VIDEO_MIN_DURATION_SECONDS:
        pad_duration = VOLC_VIDEO_MIN_DURATION_SECONDS - input_info["duration"]
        filters.append(f"tpad=stop_mode=clone:stop_duration={pad_duration:.3f}")

    filters.append("format=yuv420p")
    return ",".join(filters)


def _build_volc_video_bitrate_limit_kbps(output_duration: float, has_audio: bool) -> int:
    duration = max(float(output_duration), VOLC_VIDEO_MIN_DURATION_SECONDS)
    audio_budget_kbps = VOLC_VIDEO_AUDIO_BITRATE_KBPS if has_audio else 0
    total_budget_kbps = int((VOLC_VIDEO_MAX_SIZE_BYTES * 8 * 0.95) / 1024 / duration)
    return max(500, total_budget_kbps - audio_budget_kbps - 64)


def _summarize_volc_video_plan(
    input_info: dict,
    geometry: dict,
    target_duration: float,
    target_fps: float,
) -> str:
    changes = []
    original_ratio = (
        float(input_info["width"]) / float(input_info["height"])
        if input_info.get("width") and input_info.get("height")
        else 0.0
    )

    if (
        geometry["crop_width"] != input_info["width"]
        or geometry["crop_height"] != input_info["height"]
        or geometry["crop_x"] != 0
        or geometry["crop_y"] != 0
    ):
        changes.append(
            "crop="
            f"{geometry['crop_width']}x{geometry['crop_height']}@"
            f"({geometry['crop_x']},{geometry['crop_y']})"
        )
    else:
        changes.append("crop=keep")

    changes.append(
        f"scale={geometry['scale_width']}x{geometry['scale_height']}"
    )

    source_duration = float(input_info.get("duration") or 0.0)
    if source_duration < VOLC_VIDEO_MIN_DURATION_SECONDS:
        changes.append(f"duration=pad {source_duration:.2f}s -> {target_duration:.2f}s")
    elif source_duration > VOLC_VIDEO_MAX_DURATION_SECONDS:
        changes.append(f"duration=trim {source_duration:.2f}s -> {target_duration:.2f}s")
    else:
        changes.append(f"duration=keep {target_duration:.2f}s")

    source_fps = float(input_info.get("fps") or 0.0)
    if source_fps <= 0:
        changes.append(f"fps=set default -> {target_fps:.2f}")
    elif abs(source_fps - target_fps) > 0.1:
        changes.append(f"fps=normalize {source_fps:.2f} -> {target_fps:.2f}")
    else:
        changes.append(f"fps=keep {target_fps:.2f}")

    changes.append(f"source_ratio={original_ratio:.4f}")
    changes.append(
        f"target_pixels={geometry['scale_width'] * geometry['scale_height']}"
    )
    return ", ".join(changes)


def _run_volc_video_transcode(
    input_path: str,
    output_path: str,
    input_info: dict,
    geometry: dict,
    target_fps: float,
    target_duration: float,
    logger_prefix: str,
    stage_label: str,
    video_bitrate_kbps: int | None = None,
):
    _require_video_tool("ffmpeg")

    filters = _build_volc_video_filters(input_info, geometry, target_fps)
    encode_mode = (
        "quality mode (CRF 23)"
        if video_bitrate_kbps is None
        else f"size-constrained mode ({int(video_bitrate_kbps)}k)"
    )
    _log_video_asset(
        logger_prefix,
        (
            f"{stage_label}: starting ffmpeg transcode, "
            f"target={geometry['scale_width']}x{geometry['scale_height']}, "
            f"duration={target_duration:.2f}s, fps={target_fps:.2f}, "
            f"audio={'keep' if input_info['has_audio'] else 'drop'}, "
            f"mode={encode_mode}"
        ),
    )

    ffmpeg_cmd = [
        "ffmpeg",
        "-y",
        "-i",
        input_path,
        "-map",
        "0:v:0",
        "-vf",
        filters,
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        "-r",
        _format_fps_value(target_fps),
    ]

    if video_bitrate_kbps is None:
        ffmpeg_cmd += ["-crf", "23"]
    else:
        ffmpeg_cmd += [
            "-b:v",
            f"{int(video_bitrate_kbps)}k",
            "-maxrate",
            f"{int(video_bitrate_kbps)}k",
            "-bufsize",
            f"{int(video_bitrate_kbps) * 2}k",
        ]

    if input_info["has_audio"]:
        ffmpeg_cmd += ["-map", "0:a:0?"]
        if input_info["duration"] < VOLC_VIDEO_MIN_DURATION_SECONDS:
            pad_duration = VOLC_VIDEO_MIN_DURATION_SECONDS - input_info["duration"]
            ffmpeg_cmd += ["-af", f"apad=pad_dur={pad_duration:.3f}"]
        ffmpeg_cmd += [
            "-c:a",
            "aac",
            "-b:a",
            f"{VOLC_VIDEO_AUDIO_BITRATE_KBPS}k",
            "-ar",
            "48000",
        ]
    else:
        ffmpeg_cmd += ["-an"]

    ffmpeg_cmd += ["-t", f"{target_duration:.3f}", output_path]

    try:
        result = subprocess.run(
            ffmpeg_cmd,
            capture_output=True,
            text=True,
            timeout=VOLC_VIDEO_FFMPEG_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as e:
        raise RuntimeError("ffmpeg timed out while preprocessing the video asset") from e

    if result.returncode != 0:
        stderr = (result.stderr or "").strip()
        raise RuntimeError(
            f"ffmpeg failed while preprocessing the video asset: {stderr[:500]}"
        )
    _log_video_asset(logger_prefix, f"{stage_label}: ffmpeg transcode completed")


def _validate_preprocessed_video_info(info: dict):
    errors = []
    format_name = str(info.get("format_name") or "").lower()
    duration = float(info.get("duration") or 0.0)
    fps = float(info.get("fps") or 0.0)
    width = int(info.get("width") or 0)
    height = int(info.get("height") or 0)
    size_bytes = int(info.get("size_bytes") or 0)
    area = width * height
    ratio = float(width) / float(height) if width > 0 and height > 0 else 0.0

    if not any(token in format_name for token in ("mp4", "mov")):
        errors.append(f"format={format_name or 'unknown'}")
    if duration < VOLC_VIDEO_MIN_DURATION_SECONDS - 0.05 or duration > VOLC_VIDEO_MAX_DURATION_SECONDS + 0.05:
        errors.append(f"duration={duration:.3f}s")
    if fps < VOLC_VIDEO_MIN_FPS - 0.1 or fps > VOLC_VIDEO_MAX_FPS + 0.1:
        errors.append(f"fps={fps:.3f}")
    if width < VOLC_VIDEO_MIN_DIMENSION or width > VOLC_VIDEO_MAX_DIMENSION:
        errors.append(f"width={width}")
    if height < VOLC_VIDEO_MIN_DIMENSION or height > VOLC_VIDEO_MAX_DIMENSION:
        errors.append(f"height={height}")
    if ratio < VOLC_VIDEO_MIN_RATIO - 0.01 or ratio > VOLC_VIDEO_MAX_RATIO + 0.01:
        errors.append(f"ratio={ratio:.4f}")
    if area < VOLC_VIDEO_MIN_PIXELS or area > VOLC_VIDEO_MAX_PIXELS:
        errors.append(f"pixels={area}")
    if size_bytes > VOLC_VIDEO_MAX_SIZE_BYTES:
        errors.append(f"size={size_bytes / (1024 * 1024):.2f}MB")

    if errors:
        raise RuntimeError(
            "Preprocessed video still does not meet Volc asset requirements: "
            + ", ".join(errors)
        )


def preprocess_video_for_volc_asset(media_value, logger_prefix: str) -> dict:
    """Normalize arbitrary VIDEO input into a Volc-compatible MP4 asset."""
    input_path = ""
    input_is_temp = False
    temp_paths = []

    try:
        input_path, input_is_temp = _materialize_video_input(media_value)
        if input_is_temp:
            temp_paths.append(input_path)
            _log_video_asset(
                logger_prefix,
                "No stable file path was available; materialized VIDEO input to a temporary file",
            )
        else:
            _log_video_asset(
                logger_prefix,
                f"Using source video file: {input_path}",
            )

        input_info = _probe_video_info(input_path)
        if input_info["duration"] <= 0:
            raise RuntimeError("Could not determine a valid duration for the VIDEO input")

        target_duration = _clamp_number(
            input_info["duration"],
            VOLC_VIDEO_MIN_DURATION_SECONDS,
            VOLC_VIDEO_MAX_DURATION_SECONDS,
        )
        target_fps = _clamp_number(
            input_info["fps"] or VOLC_VIDEO_DEFAULT_FPS,
            VOLC_VIDEO_MIN_FPS,
            VOLC_VIDEO_MAX_FPS,
        )
        geometry = _compute_volc_video_geometry(input_info["width"], input_info["height"])

        _log_video_asset(
            logger_prefix,
            "Video asset preprocessing started",
        )
        _log_video_asset(
            logger_prefix,
            f"Original video info: {_describe_video_info(input_info)}",
        )
        _log_video_asset(
            logger_prefix,
            "Normalization plan: "
            + _summarize_volc_video_plan(input_info, geometry, target_duration, target_fps),
        )

        output_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
        output_file.close()
        output_path = output_file.name
        temp_paths.append(output_path)

        _run_volc_video_transcode(
            input_path,
            output_path,
            input_info,
            geometry,
            target_fps,
            target_duration,
            logger_prefix,
            "Pass 1",
        )

        output_info = _probe_video_info(output_path)
        _log_video_asset(
            logger_prefix,
            f"Pass 1 output info: {_describe_video_info(output_info)}",
        )
        if output_info["size_bytes"] > VOLC_VIDEO_MAX_SIZE_BYTES:
            constrained_output = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
            constrained_output.close()
            constrained_output_path = constrained_output.name
            temp_paths.append(constrained_output_path)

            bitrate_limit_kbps = _build_volc_video_bitrate_limit_kbps(
                target_duration,
                input_info["has_audio"],
            )
            _log_video_asset(
                logger_prefix,
                (
                    "Pass 1 output exceeds the 50MB limit; "
                    f"starting Pass 2 with bitrate cap {bitrate_limit_kbps}k"
                ),
            )
            _run_volc_video_transcode(
                input_path,
                constrained_output_path,
                input_info,
                geometry,
                target_fps,
                target_duration,
                logger_prefix,
                "Pass 2",
                video_bitrate_kbps=bitrate_limit_kbps,
            )
            output_path = constrained_output_path
            output_info = _probe_video_info(output_path)
            _log_video_asset(
                logger_prefix,
                f"Pass 2 output info: {_describe_video_info(output_info)}",
            )

        _validate_preprocessed_video_info(output_info)

        _log_video_asset(
            logger_prefix,
            "Validation passed; video asset is ready for RH upload",
        )
        _log_video_asset(
            logger_prefix,
            f"Final video info: {_describe_video_info(output_info)}",
        )

        with open(output_path, "rb") as f:
            file_bytes = f.read()

        return {
            "file_bytes": file_bytes,
            "filename": f"asset_{abs(hash(file_bytes)) % 10**10}.mp4",
            "mime_type": "video/mp4",
        }
    except Exception as e:
        _log_video_asset(logger_prefix, f"ERROR: video asset preprocessing failed: {e}")
        raise
    finally:
        for temp_path in temp_paths:
            try:
                if temp_path and os.path.exists(temp_path):
                    os.remove(temp_path)
            except OSError:
                pass


def _normalize_asset_media_type(media_type: str) -> str:
    """Normalize media type to the asset API values."""
    value = str(media_type or "").strip().lower()
    mapping = {
        "image": "Image",
        "video": "Video",
        "audio": "Audio",
    }
    normalized = mapping.get(value)
    if not normalized:
        raise ValueError(f"Unsupported asset media type: {media_type}")
    return normalized


def _query_asset_info(asset_id: str, config, logger_prefix: str) -> dict:
    """Query asset metadata from the asset service."""
    response = post_json(
        "assets/query",
        {"assetId": asset_id},
        config["api_key"],
        config["base_url"],
        timeout=config.get("timeout", 60),
        max_retries=1,
        logger_prefix=f"{logger_prefix}_AssetQuery",
    )
    data = response.get("data") or {}
    return {
        "asset_id": clean_string(data.get("assetId")) or asset_id,
        "status": clean_string(data.get("status")),
        "preview_url": clean_string(data.get("previewUrl")),
        "asset_type": clean_string(data.get("assetType")),
        "response": response,
    }


def _asset_ready_timeout(config, media_type: str) -> int:
    """Resolve asset readiness timeout with media-aware defaults."""
    default_timeout = ASSET_READY_TIMEOUTS.get(str(media_type or "").strip().lower(), 90)
    custom_timeout = config.get("asset_ready_timeout")
    if custom_timeout is None:
        return default_timeout
    try:
        return max(5, int(custom_timeout))
    except (TypeError, ValueError):
        return default_timeout


def wait_for_asset_ready(asset_id: str, config, media_type: str, logger_prefix: str) -> dict:
    """Poll asset status until the asset is ready to be consumed."""
    timeout_seconds = _asset_ready_timeout(config, media_type)
    poll_interval = max(1, int(config.get("asset_ready_poll_interval", 2)))
    deadline = time.time() + timeout_seconds
    consecutive_failures = 0
    max_consecutive_failures = 5
    last_status = None

    while True:
        try:
            asset_info = _query_asset_info(asset_id, config, logger_prefix)
        except Exception as e:
            consecutive_failures += 1
            print(
                f"[{logger_prefix}] WARNING: asset readiness poll failed "
                f"({consecutive_failures}/{max_consecutive_failures}): {e}"
            )
            if consecutive_failures >= max_consecutive_failures:
                raise RuntimeError(f"Asset {asset_id} readiness polling failed: {e}") from e
            if time.time() >= deadline:
                raise RuntimeError(f"Timed out while waiting for asset {asset_id} to become ready") from e
            time.sleep(min(consecutive_failures * 2, 10))
            continue

        consecutive_failures = 0
        status = clean_string(asset_info.get("status")).upper()
        if status != last_status:
            print(f"[{logger_prefix}] Asset {asset_id} status={status or 'UNKNOWN'}")
            last_status = status

        if status in ASSET_READY_STATUSES:
            return asset_info

        if status in ASSET_FAILED_STATUSES:
            raise RuntimeError(f"Asset {asset_id} processing failed with status: {status}")

        if time.time() >= deadline:
            raise RuntimeError(
                f"Timed out after {timeout_seconds}s waiting for asset {asset_id} to become ready "
                f"(last status: {status or 'unknown'})"
            )

        time.sleep(poll_interval)


def _upload_media_for_asset(config, media_type: str, media_value, logger_prefix: str) -> dict:
    """Upload local media and return the fixed asset payload parts."""
    asset_type = _normalize_asset_media_type(media_type)

    if asset_type == "Image":
        prepared_image = preprocess_image_for_volc_asset(media_value, logger_prefix)
        file_bytes = prepared_image["file_bytes"]
        filename = prepared_image["filename"]
        mime_type = prepared_image["mime_type"]
        upload_timeout = config.get("upload_timeout", 60)
    elif asset_type == "Video":
        prepared_video = preprocess_video_for_volc_asset(media_value, logger_prefix)
        file_bytes = prepared_video["file_bytes"]
        filename = prepared_video["filename"]
        mime_type = prepared_video["mime_type"]
        upload_timeout = max(config.get("upload_timeout", 60), 120)
    else:
        prepared_audio = preprocess_audio_for_volc_asset(media_value, logger_prefix)
        file_bytes = prepared_audio["file_bytes"]
        filename = prepared_audio["filename"]
        mime_type = prepared_audio["mime_type"]
        upload_timeout = config.get("upload_timeout", 60)

    source_url = upload_file(
        file_bytes,
        filename,
        mime_type,
        config["api_key"],
        config["base_url"],
        timeout=upload_timeout,
        logger_prefix=logger_prefix,
    )
    return {
        "groupId": FIXED_ASSET_GROUP_ID,
        "url": source_url,
        "assetType": asset_type,
        "name": FIXED_ASSET_NAME,
    }


def prepare_fixed_asset_create_payload(config, media_type: str, media_value, logger_prefix: str) -> dict:
    """Prepare a fixed asset-create payload from local media."""
    return _upload_media_for_asset(config, media_type, media_value, logger_prefix)


def create_fixed_asset_from_media(config, media_type: str, media_value, logger_prefix: str) -> dict:
    """Create a fixed asset from local media and return asset metadata."""
    payload = prepare_fixed_asset_create_payload(config, media_type, media_value, logger_prefix)
    response = post_json(
        "assets/create",
        payload,
        config["api_key"],
        config["base_url"],
        timeout=config.get("timeout", 60),
        logger_prefix=f"{logger_prefix}_AssetCreate",
    )
    data = response.get("data") or {}
    asset_id = clean_string(data.get("assetId"))
    if not asset_id:
        raise RuntimeError("No assetId returned from asset create API")
    ready_info = wait_for_asset_ready(
        asset_id,
        config,
        media_type,
        f"{logger_prefix}_AssetReady",
    )
    return {
        "asset_id": asset_id,
        "asset_url": f"asset://{asset_id}",
        "status": clean_string(ready_info.get("status")) or clean_string(data.get("status")),
        "response": ready_info.get("response") or response,
    }


def _split_asset_ids(*values) -> list:
    """Flatten raw asset id inputs into a clean ordered list."""
    result = []
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if not text:
            continue
        parts = re.split(r"[\n,]+", text)
        for part in parts:
            asset_id = clean_string(part)
            if not asset_id:
                continue
            if asset_id.startswith("asset://"):
                asset_id = asset_id[8:]
            result.append(asset_id)
    return result


class RH_SparkVideoAssetCreate(AssetRestNodeBase):
    ENDPOINT = "assets/create"
    RETURN_TYPES = ("STRING", "STRING", "STRING")
    RETURN_NAMES = ("asset_id", "status", "response")

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {},
            "optional": {
                "image": ("IMAGE",),
                "video": ("VIDEO",),
                "audio": ("AUDIO",),
                **cls.common_optional_inputs(),
            },
        }

    def prepare_payload(self, config, image=None, video=None, audio=None, **kwargs):
        media_inputs = []
        if image is not None:
            media_inputs.append(("Image", image))
        if video is not None:
            media_inputs.append(("Video", video))
        if audio is not None:
            media_inputs.append(("Audio", audio))

        if len(media_inputs) == 0:
            raise ValueError("Exactly one of image, video, or audio must be provided")
        if len(media_inputs) > 1:
            names = [name for name, _ in media_inputs]
            raise ValueError(
                f"Only one media input is allowed, but got {len(media_inputs)}: {', '.join(names)}"
            )

        asset_type, media_value = media_inputs[0]
        return prepare_fixed_asset_create_payload(config, asset_type, media_value, self._log_prefix)

    def parse_response(self, response, config=None, image=None, video=None, audio=None, **kwargs):
        data = response.get("data") or {}
        asset_id = clean_string(data.get("assetId"))
        status = clean_string(data.get("status"))
        final_response = response

        media_type = ""
        if image is not None:
            media_type = "image"
        elif video is not None:
            media_type = "video"
        elif audio is not None:
            media_type = "audio"

        if config is not None and asset_id:
            ready_info = wait_for_asset_ready(
                asset_id,
                config,
                media_type,
                f"{self._log_prefix}_AssetReady",
            )
            status = clean_string(ready_info.get("status")) or status
            final_response = ready_info.get("response") or response

        return (
            asset_id,
            status,
            self._response_json(final_response),
        )


class RH_SparkVideoAssetList(AssetRestNodeBase):
    ENDPOINT = "assets/list"
    RETURN_TYPES = ("STRING", "STRING", "STRING")
    RETURN_NAMES = ("items_json", "total_count", "response")

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "page_number": ("INT", {"default": 1, "min": 1, "max": 9999}),
                "page_size": ("INT", {"default": 20, "min": 1, "max": 100}),
            },
            "optional": {
                "group_id": connectable_string_input(),
                "status": text_input(),
                "name": text_input(),
                **cls.common_optional_inputs(),
            },
        }

    def build_payload(self, page_number, page_size, group_id="", status="", name="", **kwargs):
        payload = {
            "pageNumber": int(page_number),
            "pageSize": int(page_size),
        }

        group_id = clean_string(group_id)
        status = clean_string(status)
        name = clean_string(name)

        if group_id:
            payload["groupId"] = group_id
        if status:
            payload["status"] = status
        if name:
            payload["name"] = name

        return payload

    def parse_response(self, response, **kwargs):
        data = response.get("data") or {}
        items = data.get("items") or []
        return (
            dumps_json(items),
            clean_string(data.get("totalCount")),
            self._response_json(response),
        )


class RH_SparkVideoAssetQuery(AssetRestNodeBase):
    ENDPOINT = "assets/query"
    RETURN_TYPES = ("STRING", "STRING", "STRING", "STRING")
    RETURN_NAMES = ("asset_id", "status", "preview_url", "response")

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "asset_id": connectable_string_input(),
            },
            "optional": cls.common_optional_inputs(),
        }

    def build_payload(self, asset_id, **kwargs):
        return {"assetId": self._require_string("asset_id", asset_id)}

    def parse_response(self, response, **kwargs):
        data = response.get("data") or {}
        return (
            clean_string(data.get("assetId")),
            clean_string(data.get("status")),
            clean_string(data.get("previewUrl")),
            self._response_json(response),
        )


class RH_SparkVideoAssetIdsMerge:
    CATEGORY = "RunningHub/SparkVideo Assets"
    FUNCTION = "merge"
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("asset_ids",)

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "asset_id1": connectable_string_input(),
            },
            "optional": {
                "asset_id2": connectable_string_input(),
                "asset_id3": connectable_string_input(),
                "asset_id4": connectable_string_input(),
                "asset_id5": connectable_string_input(),
                "asset_id6": connectable_string_input(),
                "asset_id7": connectable_string_input(),
                "asset_id8": connectable_string_input(),
                "asset_id9": connectable_string_input(),
                "asset_id10": connectable_string_input(),
            },
        }

    def merge(
        self,
        asset_id1,
        asset_id2="",
        asset_id3="",
        asset_id4="",
        asset_id5="",
        asset_id6="",
        asset_id7="",
        asset_id8="",
        asset_id9="",
        asset_id10="",
    ):
        asset_ids = _split_asset_ids(
            asset_id1,
            asset_id2,
            asset_id3,
            asset_id4,
            asset_id5,
            asset_id6,
            asset_id7,
            asset_id8,
            asset_id9,
            asset_id10,
        )
        if not asset_ids:
            raise ValueError("At least one asset_id is required")
        return (", ".join(asset_ids),)


class RH_SparkVideoAssetUpdate(AssetRestNodeBase):
    ENDPOINT = "assets/update"
    RETURN_TYPES = ("STRING", "STRING", "STRING", "STRING")
    RETURN_NAMES = ("asset_id", "name", "status", "response")

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "asset_id": connectable_string_input(),
                "name": text_input(),
            },
            "optional": cls.common_optional_inputs(),
        }

    def build_payload(self, asset_id, name, **kwargs):
        return {
            "assetId": self._require_string("asset_id", asset_id),
            "name": self._require_string("name", name),
        }

    def parse_response(self, response, **kwargs):
        data = response.get("data") or {}
        return (
            clean_string(data.get("assetId")),
            clean_string(data.get("name")),
            clean_string(data.get("status")),
            self._response_json(response),
        )


class RH_SparkVideoAssetDelete(AssetRestNodeBase):
    ENDPOINT = "assets/delete"
    RETURN_TYPES = ("STRING", "STRING", "STRING")
    RETURN_NAMES = ("asset_id", "status", "response")

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "asset_id": connectable_string_input(),
            },
            "optional": cls.common_optional_inputs(),
        }

    def build_payload(self, asset_id, **kwargs):
        return {"assetId": self._require_string("asset_id", asset_id)}

    def parse_response(self, response, asset_id="", **kwargs):
        return (
            clean_string(asset_id),
            "deleted",
            self._response_json(response),
        )
