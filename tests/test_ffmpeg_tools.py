import importlib
import io
import os
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from types import ModuleType
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class _FakeResponse:
    def __init__(self, payload: bytes):
        self.payload = payload

    def raise_for_status(self):
        return None

    def iter_content(self, chunk_size: int = 1024 * 1024):
        for offset in range(0, len(self.payload), chunk_size):
            yield self.payload[offset: offset + chunk_size]

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class FFmpegToolTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        package_name = "ffmpeg_tools_test_pkg"
        if package_name not in sys.modules:
            module = ModuleType(package_name)
            module.__path__ = [str(PROJECT_ROOT)]
            sys.modules[package_name] = module
        cls.ffmpeg_tools = importlib.import_module(f"{package_name}.core.ffmpeg_tools")

    def setUp(self):
        self.ffmpeg_tools._RESOLVED_TOOLS.clear()
        self.ffmpeg_tools._load_plugin_env.cache_clear()

    def _build_windows_release_zip(self) -> bytes:
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            archive.writestr("ffmpeg-test/bin/ffmpeg.exe", b"ffmpeg-binary")
            archive.writestr("ffmpeg-test/bin/ffprobe.exe", b"ffprobe-binary")
        return buffer.getvalue()

    def test_explicit_directory_override_resolves_sibling_binary(self):
        with tempfile.TemporaryDirectory() as temp_dir, patch.object(
            self.ffmpeg_tools,
            "_load_plugin_env",
            return_value={},
        ), patch.dict(
            os.environ,
            {
                "RH_FFMPEG_PATH": temp_dir,
                "RH_DISABLE_AUTO_FFMPEG_DOWNLOAD": "1",
            },
            clear=False,
        ):
            ffmpeg_binary = Path(temp_dir) / self.ffmpeg_tools._binary_name("ffmpeg")
            ffprobe_binary = Path(temp_dir) / self.ffmpeg_tools._binary_name("ffprobe")
            ffmpeg_binary.write_bytes(b"ffmpeg")
            ffprobe_binary.write_bytes(b"ffprobe")

            resolved = self.ffmpeg_tools.resolve_video_tool_path("ffprobe")
            self.assertEqual(Path(resolved), ffprobe_binary)

    def test_cached_binary_takes_priority_over_system_path(self):
        with tempfile.TemporaryDirectory() as temp_dir, patch.object(
            self.ffmpeg_tools,
            "_load_plugin_env",
            return_value={},
        ), patch.dict(
            os.environ,
            {
                "RH_FFMPEG_CACHE_DIR": temp_dir,
                "RH_DISABLE_AUTO_FFMPEG_DOWNLOAD": "1",
            },
            clear=False,
        ), patch.object(
            self.ffmpeg_tools.shutil,
            "which",
            return_value=str(Path(temp_dir) / "system" / self.ffmpeg_tools._binary_name("ffprobe")),
        ):
            cached_binary = Path(temp_dir) / self.ffmpeg_tools._binary_name("ffprobe")
            cached_binary.write_bytes(b"cached")

            resolved = self.ffmpeg_tools.resolve_video_tool_path("ffprobe")
            self.assertEqual(Path(resolved), cached_binary)

    def test_windows_auto_download_populates_cache_and_returns_binary(self):
        zip_payload = self._build_windows_release_zip()

        with tempfile.TemporaryDirectory() as temp_dir, patch.object(
            self.ffmpeg_tools,
            "_load_plugin_env",
            return_value={},
        ), patch.dict(
            os.environ,
            {
                "RH_FFMPEG_CACHE_DIR": temp_dir,
            },
            clear=False,
        ), patch.object(
            self.ffmpeg_tools.os,
            "name",
            "nt",
        ), patch.object(
            self.ffmpeg_tools.shutil,
            "which",
            return_value=None,
        ), patch.object(
            self.ffmpeg_tools.requests,
            "get",
            return_value=_FakeResponse(zip_payload),
        ):
            resolved = self.ffmpeg_tools.resolve_video_tool_path("ffprobe")
            cache_dir = Path(temp_dir)

            self.assertEqual(resolved, str(cache_dir / "ffprobe.exe"))
            self.assertEqual((cache_dir / "ffprobe.exe").read_bytes(), b"ffprobe-binary")
            self.assertEqual((cache_dir / "ffmpeg.exe").read_bytes(), b"ffmpeg-binary")


if __name__ == "__main__":
    unittest.main()
