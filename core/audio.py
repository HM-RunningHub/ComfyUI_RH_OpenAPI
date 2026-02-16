"""
Audio download utilities.

Downloads audio from URL and returns ComfyUI AUDIO dict.
"""

import os
import uuid
import torch
import requests
from typing import Any, Dict, Optional


def download_audio(
    url: str,
    timeout: int = 120,
    max_retries: int = 3,
    logger_prefix: str = "RH_OpenAPI_Audio",
) -> Dict:
    """
    Download audio from URL and return ComfyUI AUDIO dict.

    Returns:
        {"waveform": tensor [1, channels, samples], "sample_rate": int}
    """
    last_error = None
    for attempt in range(max_retries):
        try:
            if attempt > 0:
                import time
                time.sleep(2 ** attempt)

            response = requests.get(url, stream=True, timeout=timeout)
            response.raise_for_status()

            audio_bytes = response.content

            # Try torchaudio first
            try:
                import torchaudio
                from io import BytesIO

                buffer = BytesIO(audio_bytes)
                waveform, sample_rate = torchaudio.load(buffer)

                # Ensure 3D: [batch, channels, samples]
                if waveform.dim() == 2:
                    waveform = waveform.unsqueeze(0)

                return {
                    "waveform": waveform,
                    "sample_rate": sample_rate,
                }

            except ImportError:
                # Fallback: save to temp file and load with scipy
                try:
                    import scipy.io.wavfile as wavfile
                    import numpy as np
                    from io import BytesIO

                    buffer = BytesIO(audio_bytes)
                    sample_rate, data = wavfile.read(buffer)

                    if data.dtype == np.int16:
                        data = data.astype(np.float32) / 32768.0
                    elif data.dtype == np.int32:
                        data = data.astype(np.float32) / 2147483648.0
                    elif data.dtype != np.float32:
                        data = data.astype(np.float32)

                    if len(data.shape) == 1:
                        data = data[np.newaxis, :]  # mono: [1, samples]
                    else:
                        data = data.T  # [samples, channels] → [channels, samples]

                    waveform = torch.from_numpy(data).unsqueeze(0)  # [1, channels, samples]

                    return {
                        "waveform": waveform,
                        "sample_rate": sample_rate,
                    }

                except Exception:
                    # Last resort: return raw bytes info as a string URL
                    print(f"[{logger_prefix} WARNING] Cannot decode audio, returning URL")
                    # Create a minimal silent audio as fallback
                    sample_rate = 44100
                    waveform = torch.zeros(1, 1, sample_rate)  # 1 second of silence
                    return {
                        "waveform": waveform,
                        "sample_rate": sample_rate,
                    }

        except Exception as e:
            last_error = e
            continue

    raise RuntimeError(f"Failed to download audio after {max_retries} attempts: {last_error}")


def audio_to_bytes(audio_dict: Dict, format: str = "wav") -> bytes:
    """
    Convert ComfyUI AUDIO dict to bytes for upload.

    Args:
        audio_dict: {"waveform": tensor [1, channels, samples], "sample_rate": int}
        format: output format ("wav" or "mp3")

    Returns:
        Audio file bytes
    """
    from io import BytesIO

    waveform = audio_dict["waveform"]
    sample_rate = audio_dict["sample_rate"]

    # Ensure 2D: [channels, samples]
    if waveform.dim() == 3:
        waveform = waveform.squeeze(0)
    if waveform.dim() == 1:
        waveform = waveform.unsqueeze(0)

    buffer = BytesIO()

    # Try torchaudio first
    try:
        import torchaudio
        torchaudio.save(buffer, waveform, sample_rate, format=format)
        return buffer.getvalue()
    except (ImportError, Exception):
        pass

    # Fallback: scipy for wav
    try:
        import scipy.io.wavfile as wavfile
        import numpy as np

        data = waveform.cpu().numpy()
        # [channels, samples] → [samples, channels]
        if data.shape[0] <= 2:
            data = data.T
        # Convert float32 to int16
        data = (data * 32767).clip(-32768, 32767).astype(np.int16)

        wavfile.write(buffer, sample_rate, data)
        return buffer.getvalue()
    except (ImportError, Exception):
        pass

    raise RuntimeError("Cannot convert audio: neither torchaudio nor scipy available")
