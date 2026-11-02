"""Triangulate matching two-camera landmarks without guessing hidden joints."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2
import numpy as np


def projection_matrix(camera: dict) -> np.ndarray:
    # Calibration stores Blender's 4x4 clip projection and world transform.
    # This helper accepts an optional 3x4 image projection directly; callers
    # should provide that for real external-camera triangulation.
    if "projection_3x4" in camera:
        return np.asarray(camera["projection_3x4"], dtype=np.float64)
    raise ValueError("Calibration needs camera.projection_3x4 for triangulation")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("observations", type=Path, help="JSON frames with camera_A/camera_B landmarks")
    parser.add_argument("--calibration", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--min-confidence", type=float, default=0.5)
    parser.add_argument("--approval", type=Path, help="Optional approval manifest; only approved landmarks are triangulated")
    parser.add_argument("--max-frames", type=int, default=0, help="Limit processing to the first N frames; 0 means all")
    args = parser.parse_args()
    obs = json.loads(args.observations.read_text(encoding="utf-8"))
    cal = json.loads(args.calibration.read_text(encoding="utf-8"))
    approvals = {}
    if args.approval:
        approval_data = json.loads(args.approval.read_text(encoding="utf-8"))
        approvals = {name: item.get("status") == "approved" for name, item in approval_data.get("landmarks", {}).items()}
    cameras = cal.get("cameras", {})
    pa = projection_matrix(cameras["A_side"])
    pb = projection_matrix(cameras["B_front"])
    frames = obs.get("frames", obs if isinstance(obs, list) else [])
    if args.max_frames > 0:
        frames = frames[:args.max_frames]
    result_frames = []
    for frame in frames:
        a = frame.get("camera_A", {}).get("landmarks", {})
        b = frame.get("camera_B", {}).get("landmarks", {})
        names = sorted(set(a) | set(b))
        joints = {}
        for name in names:
            va, vb = a.get(name), b.get(name)
            if args.approval and not approvals.get(name, False):
                joints[name] = {"state": "uncertain", "reason": "landmark_not_approved"}
                continue
            # Expected format: {x, y, visible, confidence}; hidden points are
            # retained as uncertain metadata, never filled from a guess.
            if not va or not vb or not va.get("visible") or not vb.get("visible"):
                joints[name] = {"state": "uncertain", "reason": "hidden_or_missing_in_one_view"}
                continue
            if min(float(va.get("confidence", 0.0)), float(vb.get("confidence", 0.0))) < args.min_confidence:
                joints[name] = {"state": "uncertain", "reason": "low_confidence"}
                continue
            xa = np.array([[float(va["x"])], [float(va["y"])]], dtype=np.float64)
            xb = np.array([[float(vb["x"])], [float(vb["y"])]], dtype=np.float64)
            homogeneous = cv2.triangulatePoints(pa, pb, xa, xb)
            xyz = (homogeneous[:3, 0] / homogeneous[3, 0]).tolist()
            joints[name] = {"state": "triangulated", "xyz": xyz, "confidence": min(float(va.get("confidence", 0.0)), float(vb.get("confidence", 0.0)))}
        result_frames.append({"frame": frame.get("frame"), "joints": joints})
    result = {"source": str(args.observations), "frames": result_frames, "approval_manifest": str(args.approval) if args.approval else None, "note": "Uncertain or unapproved joints were not triangulated or guessed."}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(args.output), "frames": len(result_frames)}, indent=2))


if __name__ == "__main__":
    main()
