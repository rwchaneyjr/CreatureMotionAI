"""Reject detector landmarks that fall outside a coarse foreground mask."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2
import numpy as np


def foreground(image: np.ndarray) -> np.ndarray:
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    mask = ((hsv[:, :, 1] > 35) & (hsv[:, :, 2] < 250)).astype(np.uint8) * 255
    kernel = np.ones((5, 5), np.uint8)
    return cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("video", type=Path)
    parser.add_argument("proposals", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--radius", type=int, default=8)
    args = parser.parse_args()
    data = json.loads(args.proposals.read_text(encoding="utf-8"))
    rows = data.get("frames", [])
    cap = cv2.VideoCapture(str(args.video))
    if not cap.isOpened():
        raise RuntimeError(f"Could not open {args.video}")
    accepted = rejected = 0
    output_rows = []
    for row in rows:
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(row["frame"]) - 1)
        ok, frame = cap.read()
        if not ok:
            continue
        mid = frame.shape[1] // 2
        result = {"frame": row["frame"]}
        for camera, x0 in (("camera_A", 0), ("camera_B", mid)):
            panel = frame[:, x0:x0 + mid]
            mask = foreground(panel)
            landmarks = {}
            for name, item in row[camera]["landmarks"].items():
                x, y = int(round(item["x"])), int(round(item["y"]))
                x1, x2 = max(0, x - args.radius), min(mid, x + args.radius + 1)
                y1, y2 = max(0, y - args.radius), min(panel.shape[0], y + args.radius + 1)
                inside = bool(mask[y1:y2, x1:x2].mean() > 40) if x1 < x2 and y1 < y2 else False
                new_item = dict(item)
                new_item["visible"] = inside
                new_item["state"] = "proposal_in_foreground" if inside else "uncertain_outside_foreground"
                new_item["confidence"] = float(item.get("confidence", 0.0)) if inside else 0.0
                landmarks[name] = new_item
                accepted += int(inside)
                rejected += int(not inside)
            result[camera] = {"landmarks": landmarks}
        output_rows.append(result)
    cap.release()
    result = dict(data)
    result["frames"] = output_rows
    result["status"] = "foreground_filtered_proposals"
    result["accepted_points"] = accepted
    result["rejected_points"] = rejected
    result["note"] = "Foreground filtering is only a safety gate; accepted points still require review and confidence calibration."
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(args.output), "accepted_points": accepted, "rejected_points": rejected}, indent=2))


if __name__ == "__main__":
    main()
