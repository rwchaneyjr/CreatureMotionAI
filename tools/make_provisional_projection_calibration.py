"""Create provisional pinhole projections for a two-camera diagnostic test."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np


def look_at(position, target=(0.0, 0.0, 0.2)):
    p, t = np.asarray(position, float), np.asarray(target, float)
    forward = (t - p) / np.linalg.norm(t - p)
    up = np.array([0.0, 0.0, 1.0])
    right = np.cross(forward, up); right /= np.linalg.norm(right)
    true_up = np.cross(right, forward)
    R = np.vstack([right, true_up, -forward])
    return np.hstack([R, (-R @ p.reshape(3, 1))])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--width", type=int, required=True)
    parser.add_argument("--height", type=int, required=True)
    parser.add_argument("--side-distance", type=float, default=3.0)
    parser.add_argument("--front-distance", type=float, default=3.0)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    focal = float(args.width) * 52.0 / 36.0
    K = np.array([[focal, 0, args.width / 2], [0, focal, args.height / 2], [0, 0, 1]], float)
    cameras = {}
    for name, position in (("A_side", (-args.side_distance, 0.0, 0.0)), ("B_front", (0.0, -args.front_distance, 0.45))):
        Rt = look_at(position)
        cameras[name] = {"projection_3x4": (K @ Rt).tolist(), "position": list(position), "provisional": True}
    result = {"resolution": [args.width, args.height], "cameras": cameras, "provisional": True, "note": "Approximate diagnostic projections only; external lens calibration is not known."}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(args.output), "resolution": [args.width, args.height], "provisional": True}, indent=2))


if __name__ == "__main__":
    main()
