"""Validate provisional two-view 3D landmarks before pose fitting."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("triangulation", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--min-joints", type=int, default=3)
    args = parser.parse_args()
    data = json.loads(args.triangulation.read_text(encoding="utf-8"))
    frame_reports = []
    invalid = 0
    for frame in data.get("frames", []):
        valid = 0
        reasons = []
        for name, item in frame.get("joints", {}).items():
            if item.get("state") != "triangulated":
                continue
            xyz = item.get("xyz", [])
            finite = len(xyz) == 3 and all(math.isfinite(float(v)) for v in xyz)
            if not finite:
                invalid += 1
                reasons.append(f"{name}:nonfinite")
                continue
            valid += 1
        accepted = valid >= args.min_joints and not reasons
        frame_reports.append({"frame": frame.get("frame"), "triangulated_joints": valid, "accepted_for_fit": accepted, "reasons": reasons})
    accepted_frames = sum(int(x["accepted_for_fit"]) for x in frame_reports)
    result = {"source": str(args.triangulation), "frames": frame_reports, "accepted_frames": accepted_frames, "total_frames": len(frame_reports), "invalid_points": invalid, "ready_for_pose_fit": accepted_frames > 0 and invalid == 0, "note": "This is a structural safety check, not proof of anatomical accuracy."}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(args.output), "accepted_frames": accepted_frames, "total_frames": len(frame_reports), "invalid_points": invalid, "ready_for_pose_fit": result["ready_for_pose_fit"]}, indent=2))


if __name__ == "__main__":
    main()
