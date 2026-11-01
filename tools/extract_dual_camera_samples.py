"""Extract synchronized review frames from a validated split-screen MP4."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--count", type=int, default=5)
    args = parser.parse_args()
    if args.count < 2:
        raise ValueError("--count must be at least 2")

    cap = cv2.VideoCapture(str(args.input))
    if not cap.isOpened():
        raise RuntimeError(f"Could not open {args.input}")
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    if total < 1:
        cap.release()
        raise RuntimeError("Input contains no frames")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    indices = sorted({round(i * (total - 1) / (args.count - 1)) for i in range(args.count)})
    written = []
    for index in indices:
        cap.set(cv2.CAP_PROP_POS_FRAMES, index)
        ok, frame = cap.read()
        if not ok:
            continue
        mid = frame.shape[1] // 2
        left, right = frame[:, :mid], frame[:, mid:]
        label = f"frame_{index + 1:06d}"
        split_path = args.output_dir / f"{label}_split.png"
        left_path = args.output_dir / f"{label}_camera_A.png"
        right_path = args.output_dir / f"{label}_camera_B.png"
        cv2.imwrite(str(split_path), frame)
        cv2.imwrite(str(left_path), left)
        cv2.imwrite(str(right_path), right)
        written.append({"frame": index + 1, "split": str(split_path), "camera_A": str(left_path), "camera_B": str(right_path)})
    cap.release()
    report = {"input": str(args.input), "total_frames": total, "requested_count": args.count, "written": written}
    report_path = args.output_dir / "dual_camera_sample_report.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
