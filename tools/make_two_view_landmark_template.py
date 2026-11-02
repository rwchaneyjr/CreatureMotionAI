"""Create an uncertainty-first landmark template for a split-screen video."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2


DEFAULT_JOINTS = [
    "root", "body_01", "body_02", "body_03", "head_01", "head_02",
    *[f"leg_{i:02d}_{part}" for i in range(1, 9) for part in ("hip", "knee", "foot")],
    *[f"tail_{i:02d}" for i in range(1, 9)],
]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("video", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--stride", type=int, default=1)
    args = parser.parse_args()
    if args.stride < 1:
        raise ValueError("--stride must be positive")
    cap = cv2.VideoCapture(str(args.video))
    if not cap.isOpened():
        raise RuntimeError(f"Could not open {args.video}")
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = float(cap.get(cv2.CAP_PROP_FPS) or 24.0)
    cap.release()
    if width % 2:
        raise ValueError("Split-screen width must be even")
    frames = []
    for frame_number in range(1, total + 1, args.stride):
        missing = {name: {"visible": False, "confidence": 0.0, "state": "uncertain"} for name in DEFAULT_JOINTS}
        frames.append({"frame": frame_number, "camera_A": {"landmarks": missing.copy()}, "camera_B": {"landmarks": missing.copy()}})
    result = {
        "source_video": str(args.video),
        "fps": fps,
        "frame_count": total,
        "panel_resolution": [width // 2, height],
        "joint_names": DEFAULT_JOINTS,
        "frames": frames,
        "status": "template_only",
        "note": "All landmarks begin uncertain. Detector or reviewer must provide evidence before triangulation.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(args.output), "frames": len(frames), "joints_per_view": len(DEFAULT_JOINTS)}, indent=2))


if __name__ == "__main__":
    main()
