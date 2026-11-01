"""Validate temporal consistency of a synchronized two-panel reference MP4."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2
import numpy as np


def _motion_series(path: Path, max_frames: int = 120) -> tuple[list[float], float, int]:
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        raise RuntimeError(f"Could not open {path}")
    fps = float(cap.get(cv2.CAP_PROP_FPS) or 30.0)
    previous = None
    values: list[float] = []
    count = 0
    while count < max_frames:
        ok, frame = cap.read()
        if not ok:
            break
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.resize(gray, (160, 90), interpolation=cv2.INTER_AREA)
        if previous is not None:
            flow = cv2.calcOpticalFlowFarneback(previous, gray, None, 0.5, 2, 15, 2, 5, 1.1, 0)
            values.append(float(np.linalg.norm(flow, axis=2).mean()))
        previous = gray
        count += 1
    cap.release()
    return values, fps, count


def validate(input_path: Path, max_frames: int = 120) -> dict:
    cap = cv2.VideoCapture(str(input_path))
    if not cap.isOpened():
        raise RuntimeError(f"Could not open {input_path}")
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    metadata_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    cap.release()
    if width % 2:
        raise ValueError("Split-screen video width must be even")

    # Decode temporary panel streams directly from the original to avoid codec drift.
    cap = cv2.VideoCapture(str(input_path))
    left_values: list[float] = []
    right_values: list[float] = []
    previous_left = previous_right = None
    decoded = 0
    while decoded < max_frames:
        ok, frame = cap.read()
        if not ok:
            break
        mid = frame.shape[1] // 2
        panels = (frame[:, :mid], frame[:, mid:])
        current = [cv2.resize(cv2.cvtColor(p, cv2.COLOR_BGR2GRAY), (160, 90), interpolation=cv2.INTER_AREA) for p in panels]
        if previous_left is not None:
            for prev, now, out in ((previous_left, current[0], left_values), (previous_right, current[1], right_values)):
                flow = cv2.calcOpticalFlowFarneback(prev, now, None, 0.5, 2, 15, 2, 5, 1.1, 0)
                out.append(float(np.linalg.norm(flow, axis=2).mean()))
        previous_left, previous_right = current
        decoded += 1
    cap.release()

    n = min(len(left_values), len(right_values))
    correlation = None
    if n >= 3 and np.std(left_values[:n]) > 1e-8 and np.std(right_values[:n]) > 1e-8:
        correlation = float(np.corrcoef(left_values[:n], right_values[:n])[0, 1])
    # Correlation is a warning signal, not proof of geometric correctness.
    # When max_frames limits the sample, do not compare the sample length with
    # the full container frame count. The splitter already performs the full
    # decode/count validation.
    sampled_to_limit = decoded >= max_frames
    valid = decoded > 1 and (sampled_to_limit or metadata_frames == 0 or abs(metadata_frames - decoded) <= 1)
    warnings = []
    if correlation is None:
        warnings.append("Insufficient motion variation for a correlation estimate.")
    elif correlation < 0.25:
        warnings.append("Panel motion is weakly correlated; views may be unsynchronized or contain different takes.")
    report = {
        "input": str(input_path),
        "width": width,
        "height": height,
        "panel_width": width // 2,
        "metadata_frame_count": metadata_frames,
        "decoded_frame_count": decoded,
        "sampled_motion_frames": n,
        "left_fps": 0.0,
        "right_fps": 0.0,
        "motion_correlation": correlation,
        "valid_container": valid,
        "ready_for_triangulation": bool(valid and correlation is not None and correlation >= 0.25),
        "warnings": warnings,
    }
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-frames", type=int, default=120)
    args = parser.parse_args()
    report = validate(args.input, args.max_frames)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    if not report["valid_container"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
