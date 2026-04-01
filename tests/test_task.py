import unittest

from core import task


class TaskErrorMessageTests(unittest.TestCase):
    def test_real_person_rejection_adds_hint_for_supported_sparkvideo_nodes(self):
        message = task._enhance_api_error_message(
            "Photorealistic real people are prohibited, please modify your prompt or image",
            "1505",
            "RH_OpenAPI_RhartVideoSparkvideo20MultimodalVideo",
        )

        self.assertIn("real_person_mode", message)
        self.assertIn("不支持真人", message)
        self.assertIn("名人", message)
        self.assertIn("IP", message)

    def test_real_person_rejection_keeps_original_for_unsupported_nodes(self):
        original = "Photorealistic real people are prohibited, please modify your prompt or image"

        message = task._enhance_api_error_message(
            original,
            "1505",
            "RH_OpenAPI_RhartVideoSparkvideo20TextToVideo",
        )

        self.assertEqual(message, original)


if __name__ == "__main__":
    unittest.main()
