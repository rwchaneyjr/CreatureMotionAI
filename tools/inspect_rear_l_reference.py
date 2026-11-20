"""Inspect a predicted Rear.L track against the exact 24-frame reference clip.

Diagnostic only: colored points are unverified tracker predictions.
"""
import argparse
import json
from pathlib import Path

import cv2
import numpy as np


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--track", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    track = json.loads(args.track.read_text(encoding="utf-8"))
    rows = {int(row["frame"]): row for row in track["frames"]}
    capture = cv2.VideoCapture(str(args.video))
    if not capture.isOpened():
        raise RuntimeError(f"Cannot open video: {args.video}")
    colors = {"hip": (0, 0, 255), "knee": (0, 170, 255),
              "ankle": (0, 255, 255), "foot": (0, 255, 0)}
    report = []
    for frame in (1, 6, 12, 18, 24):
        capture.set(cv2.CAP_PROP_POS_FRAMES, frame - 1)
        ok, image = capture.read()
        if not ok:
            raise RuntimeError(f"Cannot read frame {frame}")
        row = rows[frame]
        for label, uv in row["landmarks_2d"].items():
            x, y = (round(float(v)) for v in uv)
            cv2.drawMarker(image, (x, y), colors[label], cv2.MARKER_CROSS, 24, 2)
            cv2.putText(image, f"{label} {row['confidence'][label]:.2f}",
                        (x + 12, y - 8), cv2.FONT_HERSHEY_SIMPLEX, .7,
                        colors[label], 2, cv2.LINE_AA)
        cv2.putText(image, f"frame {frame} / predicted Rear.L, UNVERIFIED",
                    (12, 30), cv2.FONT_HERSHEY_SIMPLEX, .8, (0, 0, 0), 3)
        cv2.putText(image, f"frame {frame} / predicted Rear.L, UNVERIFIED",
                    (12, 30), cv2.FONT_HERSHEY_SIMPLEX, .8, (255, 255, 255), 1)
        cv2.imwrite(str(args.output / f"track_{frame:02}.png"), image)
        report.append({"frame": frame, "landmarks": row["landmarks_2d"],
                       "confidence": row["confidence"]})
    capture.release()
    (args.output / "track_inspection.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
