"""Assemble a seamless five-second Fly -> Land -> Fly preview from renders."""
from pathlib import Path
import json

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/generated/dragon_quadruped_compatibility/fly_and_land"
FPS = 24
FRAME_COUNT = 120
SIZE = (800, 450)


def read_frame(folder: str, index: int) -> np.ndarray:
    path = OUT / folder / f"frame_{index:04d}.png"
    frame = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if frame is None:
        raise FileNotFoundError(f"Missing or unreadable rendered frame: {path}")
    frame = cv2.flip(frame, 1)  # Match the reference's head/tail direction.
    if (frame.shape[1], frame.shape[0]) != SIZE:
        frame = cv2.resize(frame, SIZE, interpolation=cv2.INTER_AREA)
    return frame


def main() -> None:
    # Existing Land is a 24-frame smooth transition from the airborne pose to
    # the grounded RUN pose, followed by a hold. Reverse it for takeoff so the
    # cycle returns to its exact initial pose without editing the Blender rig.
    sequence = []
    sequence.extend(read_frame("fly_frames", 1) for _ in range(48))
    sequence.extend(read_frame("land_frames", i) for i in range(1, 25))
    sequence.extend(read_frame("land_frames", 24) for _ in range(24))
    sequence.extend(read_frame("land_frames", i) for i in range(24, 0, -1))
    if len(sequence) != FRAME_COUNT:
        raise RuntimeError(f"Expected {FRAME_COUNT} frames; built {len(sequence)}")

    path = OUT / "dragon_fly_land_loop_5sec.mp4"
    writer = cv2.VideoWriter(
        str(path), cv2.VideoWriter_fourcc(*"mp4v"), FPS, SIZE
    )
    if not writer.isOpened():
        raise RuntimeError(f"Could not create MP4: {path}")
    for frame in sequence:
        writer.write(frame)
    writer.release()

    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        raise RuntimeError(f"Could not reopen generated MP4: {path}")
    count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    first_ok, first = cap.read()
    cap.set(cv2.CAP_PROP_POS_FRAMES, count - 1)
    last_ok, last = cap.read()
    cap.release()
    if count != FRAME_COUNT or not first_ok or not last_ok:
        raise RuntimeError(f"MP4 verification failed: frames={count}")
    seam_mae = float(np.abs(first.astype(np.int16) - last.astype(np.int16)).mean())
    report = {
        "status": "PASS_LOOP_VIDEO_ENCODED",
        "output": str(path),
        "fps": fps,
        "frames": count,
        "duration_seconds": count / fps,
        "sequence": [
            {"phase": "Fly hold", "frames": 48},
            {"phase": "Land to ground", "frames": 24},
            {"phase": "Grounded hold", "frames": 24},
            {"phase": "Reverse transition / takeoff", "frames": 24},
        ],
        "first_last_frame_mean_absolute_difference": seam_mae,
        "loop_note": "The transition is reversed to return to the Fly pose. It is a pose loop, not a video-captured takeoff/landing performance.",
    }
    (OUT / "dragon_fly_land_loop_report.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
