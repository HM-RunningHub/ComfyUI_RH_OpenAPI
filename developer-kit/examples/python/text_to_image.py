"""Minimal text-to-image example.

Run:
    RH_API_KEY=your-key python text_to_image.py
"""

from pathlib import Path

from client import RunningHubClient, find_model, load_registry, validate_payload


ENDPOINT = "rhart-image-v1/text-to-image"


def main() -> None:
    registry = load_registry(Path(__file__).resolve().parents[2] / "model-registry.sample.json")
    model = find_model(registry, ENDPOINT)

    payload = {
        "prompt": "A cinematic cat sitting by a neon window, highly detailed",
        "aspectRatio": "1:1",
    }
    validate_payload(model, payload)

    client = RunningHubClient()
    result = client.run(ENDPOINT, payload)
    print("task_id:", result.task_id)
    print("outputs:", result.outputs)


if __name__ == "__main__":
    main()
