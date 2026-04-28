"""Minimal image-to-image example.

Run:
    RH_API_KEY=your-key python image_to_image.py ./input.png
"""

import sys
from pathlib import Path

from client import RunningHubClient, find_model, load_registry, validate_payload


ENDPOINT = "rhart-image-v1/edit"


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit("Usage: python image_to_image.py ./input.png")

    image_path = Path(sys.argv[1])
    registry = load_registry(Path(__file__).resolve().parents[2] / "model-registry.sample.json")
    model = find_model(registry, ENDPOINT)

    payload = {
        "prompt": "Replace the background with a clean futuristic studio.",
        "aspectRatio": "auto",
    }
    validate_payload(model, {**payload, "imageUrls": ["uploaded-url-placeholder"]})

    client = RunningHubClient()
    result = client.run(
        ENDPOINT,
        payload,
        local_files={"imageUrls": [image_path]},
    )
    print("task_id:", result.task_id)
    print("outputs:", result.outputs)


if __name__ == "__main__":
    main()
