import importlib.util
import unittest
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np
from PIL import Image


spec = importlib.util.spec_from_file_location(
    "rh_image_alpha_test", Path(__file__).resolve().parents[1] / "core" / "image.py"
)
image_utils = importlib.util.module_from_spec(spec)
spec.loader.exec_module(image_utils)


class ImageAlphaTests(unittest.TestCase):
    def download(self, image):
        buf = BytesIO()
        image.save(buf, format="PNG")
        response = SimpleNamespace(content=buf.getvalue(), raise_for_status=lambda: None)
        with patch.object(image_utils.requests, "get", return_value=response):
            return image_utils.download_images_to_tensor(["https://example.test/image.png"])

    def test_download_and_save_preserve_rgba_pixels(self):
        pixels = np.array([[[12, 34, 56, 0], [78, 90, 123, 128],
                            [234, 210, 198, 255]]], dtype=np.uint8)
        tensor = self.download(Image.fromarray(pixels))
        self.assertEqual(tuple(tensor.shape), (1, 1, 3, 4))
        # Match SaveImage's tensor-to-PNG conversion, including partial alpha.
        saved = Image.fromarray(np.clip(255 * tensor[0].numpy(), 0, 255).astype(np.uint8))
        buf = BytesIO()
        saved.save(buf, format="PNG")
        np.testing.assert_array_equal(np.array(Image.open(BytesIO(buf.getvalue()))), pixels)

    def test_rgb_download_keeps_three_channels(self):
        original = Image.new("RGB", (2, 2), (23, 45, 67))
        tensor = self.download(original)
        self.assertEqual(tuple(tensor.shape), (1, 2, 2, 3))
        np.testing.assert_array_equal(np.array(image_utils.tensor_to_pil(tensor)[0]), original)

    def test_mixed_batch_promotes_rgb_to_opaque_rgba(self):
        rgb = Image.new("RGB", (2, 2), (11, 22, 33))
        rgba = Image.new("RGBA", (2, 2), (44, 55, 66, 127))
        tensor = image_utils.pil_to_tensor([rgb, rgba])
        self.assertEqual(tuple(tensor.shape), (2, 2, 2, 4))
        for actual, expected in zip(image_utils.tensor_to_pil(tensor), [rgb.convert("RGBA"), rgba]):
            np.testing.assert_array_equal(np.array(actual), np.array(expected))

    def test_palette_transparency_survives_download(self):
        original = Image.new("P", (2, 1))
        original.putpalette([12, 34, 56, 78, 90, 123] + [0] * 762)
        original.putdata([0, 1])
        original.info["transparency"] = bytes([0, 128])
        tensor = self.download(original)
        np.testing.assert_array_equal(
            np.array(image_utils.tensor_to_pil(tensor)[0]), np.array(original.convert("RGBA"))
        )

    def test_grayscale_alpha_survives_direct_conversion(self):
        original = Image.new("LA", (2, 2), (73, 128))
        tensor = image_utils.pil_to_tensor(original)
        np.testing.assert_array_equal(
            np.array(image_utils.tensor_to_pil(tensor)[0]), np.array(original.convert("RGBA"))
        )


if __name__ == "__main__":
    unittest.main()
