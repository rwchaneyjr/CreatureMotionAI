"""Render review overlays for low-confidence two-view landmark proposals."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("video", type=Path)
    parser.add_argument("proposals", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--max-frames", type=int, default=10)
    parser.add_argument("--label", action="store_true")
    args = parser.parse_args()
    data = json.loads(args.proposals.read_text(encoding="utf-8"))
    rows = data.get("frames", [])[: args.max_frames]
    cap = cv2.VideoCapture(str(args.video))
    if not cap.isOpened():
        raise RuntimeError(f"Could not open {args.video}")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for row in rows:
        frame_number = int(row["frame"])
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number - 1)
        ok, frame = cap.read()
        if not ok:
            continue
        mid = frame.shape[1] // 2
        for camera, x_offset in (("camera_A", 0), ("camera_B", mid)):
            for name, item in row.get(camera, {}).get("landmarks", {}).items():
                x = int(round(float(item["x"]) + x_offset))
                y = int(round(float(item["y"])))
                cv2.circle(frame, (x, y), 3, (0, 180, 255), -1)
                if args.label:
                    cv2.putText(frame, name, (x + 4, y - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.25, (0, 80, 255), 1, cv2.LINE_AA)
        output = args.output_dir / f"frame_{frame_number:06d}_landmarks.png"
        cv2.imwrite(str(output), frame)
        written.append(str(output))
    cap.release()
    report = {"video": str(args.video), "proposals": str(args.proposals), "written": written, "note": "Orange points are low-confidence detector proposals, not approved labels."}
    (args.output_dir / "overlay_review_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
