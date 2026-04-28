"""Minimal text-to-video example.

Run:
    RH_API_KEY=your-key python text_to_video.py
"""

from pathlib import Path

from client import RunningHubClient, find_model, load_registry, validate_payload


ENDPOINT = "rhart-video-v3.1-fast/text-to-video"


def main() -> None:
    registry = load_registry(Path(__file__).resolve().parents[2] / "model-registry.sample.json")
    model = find_model(registry, ENDPOINT)

    payload = {
        "prompt": "A calm spring afternoon, cherry blossoms falling beside a country road.",
        "aspectRatio": "16:9",
        "duration": "8",
        "resolution": "720p",
    }
    validate_payload(model, payload)

    client = RunningHubClient(max_polling_time=1800)
    result = client.run(ENDPOINT, payload)
    print("task_id:", result.task_id)
    print("outputs:", result.outputs)


if __name__ == "__main__":
    main()
