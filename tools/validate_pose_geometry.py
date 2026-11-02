"""Reject provisional frames with impossible leg segment geometry."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("triangulation", type=Path)
    parser.add_argument("constraints", type=Path)
    parser.add_argument("mapping", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--min-ratio", type=float, default=0.65)
    parser.add_argument("--max-ratio", type=float, default=1.35)
    args = parser.parse_args()
    tri = json.loads(args.triangulation.read_text(encoding="utf-8"))
    constraints = json.loads(args.constraints.read_text(encoding="utf-8"))
    mapping = json.loads(args.mapping.read_text(encoding="utf-8"))
    reports = []
    for frame in tri.get("frames", []):
        joints = frame.get("joints", {})
        failures = []
        checks = 0
        for root, leg in mapping.get("legs", {}).items():
            names = [leg["landmarks"][0], leg["landmarks"][1], leg["landmarks"][2]]
            bones = [leg["hip"], leg["knee"], leg["foot"]]
            for a, b, bone_name in zip(names, names[1:], bones[:2]):
                ja, jb = joints.get(a, {}), joints.get(b, {})
                if ja.get("state") != "triangulated" or jb.get("state") != "triangulated":
                    continue
                xyz_a, xyz_b = ja["xyz"], jb["xyz"]
                length = math.sqrt(sum((float(x) - float(y)) ** 2 for x, y in zip(xyz_a, xyz_b)))
                rest = float(constraints.get("bones", {}).get(bone_name, {}).get("length", 0.0))
                if rest <= 1e-8:
                    continue
                checks += 1
                ratio = length / rest
                if ratio < args.min_ratio or ratio > args.max_ratio:
                    failures.append({"leg": root, "bone": bone_name, "ratio": ratio, "reason": "bone_length_violation"})
        reports.append({"frame": frame.get("frame"), "checks": checks, "accepted_for_fit": bool(checks and not failures), "failures": failures})
    accepted = sum(int(x["accepted_for_fit"]) for x in reports)
    result = {"source": str(args.triangulation), "frames": reports, "accepted_frames": accepted, "total_frames": len(reports), "ready_for_bone_fit": accepted > 0, "limits": {"min_ratio": args.min_ratio, "max_ratio": args.max_ratio}, "note": "This rejects impossible geometry; it does not prove visual accuracy."}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(args.output), "accepted_frames": accepted, "total_frames": len(reports), "ready_for_bone_fit": result["ready_for_bone_fit"]}, indent=2))


if __name__ == "__main__":
    main()
