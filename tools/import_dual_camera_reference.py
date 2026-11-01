"""Import a synchronized split-screen reference and create review artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2

from split_dual_camera_video import split_video


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="One MP4 with side view on left and front view on right")
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    report = split_video(args.input, args.output_dir)

    cap = cv2.VideoCapture(str(args.input))
    ok, frame = cap.read()
    cap.release()
    if ok:
        half = frame.shape[1] // 2
        left, right = frame[:, :half], frame[:, half:]
        cv2.imwrite(str(args.output_dir / "frame_000001_camera_A.png"), left)
        cv2.imwrite(str(args.output_dir / "frame_000001_camera_B.png"), right)
        cv2.imwrite(str(args.output_dir / "frame_000001_split.png"), frame)
        report["review_frame"] = 1
        report["review_images"] = [
            "frame_000001_camera_A.png",
            "frame_000001_camera_B.png",
            "frame_000001_split.png",
        ]
        (args.output_dir / "dual_camera_video_report.json").write_text(
            json.dumps(report, indent=2), encoding="utf-8"
        )
    print(json.dumps(report, indent=2))
    if not report["valid"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
