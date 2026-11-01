"""Compare imported panel dimensions with the known Blender camera calibration."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("video", type=Path)
    parser.add_argument("--calibration", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    cap = cv2.VideoCapture(str(args.video))
    if not cap.isOpened():
        raise RuntimeError(f"Could not open {args.video}")
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = float(cap.get(cv2.CAP_PROP_FPS) or 0.0)
    frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    cap.release()
    if width % 2:
        raise ValueError("Split-screen video width must be even")

    calibration = json.loads(args.calibration.read_text(encoding="utf-8"))
    calibrated_width, calibrated_height = calibration["resolution"]
    panel_width = width // 2
    video_aspect = panel_width / height
    blender_aspect = calibrated_width / calibrated_height
    report = {
        "video": str(args.video),
        "calibration": str(args.calibration),
        "video_total_resolution": [width, height],
        "video_panel_resolution": [panel_width, height],
        "video_fps": fps,
        "video_frames": frames,
        "blender_camera_resolution": [calibrated_width, calibrated_height],
        "video_panel_aspect": video_aspect,
        "blender_aspect": blender_aspect,
        "aspect_ratio_difference": abs(video_aspect - blender_aspect),
        "requires_camera_recalibration": abs(video_aspect - blender_aspect) > 0.01,
        "note": "This compares image geometry only; it does not claim the external camera intrinsics are known.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
