"""Propagate sparse two-view landmark proposals between sampled frames."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2
import numpy as np


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("video", type=Path)
    parser.add_argument("proposals", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    data = json.loads(args.proposals.read_text(encoding="utf-8"))
    rows = data.get("frames", [])
    if len(rows) < 2:
        raise ValueError("At least two proposal frames are required")
    cap = cv2.VideoCapture(str(args.video))
    if not cap.isOpened():
        raise RuntimeError(f"Could not open {args.video}")
    frames = {}
    for number in range(1, int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0) + 1):
        ok, image = cap.read()
        if ok:
            frames[number] = image
    cap.release()
    output_rows = []
    for current, nxt in zip(rows, rows[1:]):
        output_rows.append(current)
        start, end = int(current["frame"]), int(nxt["frame"])
        for frame_number in range(start + 1, end):
            image_a = cv2.cvtColor(frames[start], cv2.COLOR_BGR2GRAY)
            image_b = cv2.cvtColor(frames[frame_number], cv2.COLOR_BGR2GRAY)
            row = {"frame": frame_number}
            for camera, offset in (("camera_A", 0), ("camera_B", image_a.shape[1] // 2)):
                points = []
                names = []
                for name, item in current[camera]["landmarks"].items():
                    if item.get("visible"):
                        points.append([float(item["x"]) + offset, float(item["y"])])
                        names.append((name, item))
                tracked = {}
                if points:
                    p0 = np.asarray(points, np.float32).reshape(-1, 1, 2)
                    p1, status, errors = cv2.calcOpticalFlowPyrLK(image_a, image_b, p0, None)
                    for (name, item), point, ok, error in zip(names, p1.reshape(-1, 2), status.reshape(-1), errors.reshape(-1)):
                        x = float(point[0] - offset)
                        y = float(point[1])
                        inside = 0 <= x < image_a.shape[1] // 2 and 0 <= y < image_a.shape[0]
                        tracked[name] = {"x": x, "y": y, "visible": bool(ok and inside and error < 25), "confidence": float(item.get("confidence", 0.0)) * 0.9, "state": "propagated" if ok and inside and error < 25 else "uncertain_tracking_failed"}
                row[camera] = {"landmarks": tracked}
            output_rows.append(row)
    output_rows.append(rows[-1])
    result = dict(data)
    result["frames"] = output_rows
    result["status"] = "optical_flow_propagated_proposals"
    result["note"] = "Propagated points are lower-confidence proposals and require review."
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(args.output), "frames": len(output_rows)}, indent=2))


if __name__ == "__main__":
    main()
