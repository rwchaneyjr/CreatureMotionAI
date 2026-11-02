"""Solve bounded two-bone leg targets without modifying Blender files."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path


def norm(v):
    return math.sqrt(sum(float(x) * float(x) for x in v))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("triangulation", type=Path)
    parser.add_argument("constraints", type=Path)
    parser.add_argument("mapping", type=Path)
    parser.add_argument("schedule", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--allow-temporal",
        action="store_true",
        help="Allow short-gap temporal_estimate landmarks as provisional inputs.",
    )
    args = parser.parse_args()
    tri = json.loads(args.triangulation.read_text(encoding="utf-8"))
    constraints = json.loads(args.constraints.read_text(encoding="utf-8"))
    mapping = json.loads(args.mapping.read_text(encoding="utf-8"))
    schedule = json.loads(args.schedule.read_text(encoding="utf-8"))["frames"]
    results = []
    for frame, plan in zip(tri.get("frames", [])[: len(schedule)], schedule):
        joints = frame.get("joints", {})
        legs = {}
        failures = []
        for root, leg in mapping.get("legs", {}).items():
            hip_name, knee_name, foot_name = leg["landmarks"]
            hip, knee, foot = (joints.get(n, {}) for n in (hip_name, knee_name, foot_name))
            allowed_states = {"triangulated"}
            if args.allow_temporal:
                allowed_states.add("temporal_estimate")
            if any(x.get("state") not in allowed_states for x in (hip, knee, foot)):
                legs[root] = {"state": "uncertain", "reason": "missing_landmark"}
                continue
            target = [float(x) for x in foot["xyz"]]
            hip_pos = [float(x) for x in hip["xyz"]]
            rest_upper = float(constraints["bones"].get(leg["hip"], {}).get("length", 0.0))
            rest_lower = float(constraints["bones"].get(leg["knee"], {}).get("length", 0.0))
            reach = rest_upper + rest_lower
            distance = norm([a - b for a, b in zip(target, hip_pos)])
            if not (0.65 * reach <= distance <= 0.98 * reach):
                failures.append({"leg": root, "reason": "target_outside_bounded_reach", "distance": distance, "reach": reach})
                legs[root] = {"state": "rejected", "distance": distance, "reach": reach}
                continue
            states = [hip.get("state"), knee.get("state"), foot.get("state")]
            legs[root] = {
                "state": "candidate",
                "foot_target": target,
                "distance": distance,
                "reach": reach,
                "provisional": any(state == "temporal_estimate" for state in states),
                "confidence": min(float(x.get("confidence", 0.0)) for x in (hip, knee, foot)),
                "preserve_rest_bend": True,
                "preserve_foot_orientation": True,
            }
        # A frame is Blender-safe only when every leg has an actual bounded
        # IK candidate.  Previously a frame with all legs marked uncertain
        # could pass merely because it had no numeric rejection, which made
        # the diagnostic scene appear usable without any targets.
        all_legs_solved = bool(legs) and all(item.get("state") == "candidate" for item in legs.values())
        results.append({
            "frame": frame.get("frame"),
            "schedule_mode": plan.get("mode"),
            "legs": legs,
            "failures": failures,
            "accepted_for_blender": all_legs_solved and not failures and plan.get("mode") != "hold_rest_pose",
        })
    accepted = sum(int(x["accepted_for_blender"]) for x in results)
    result = {"source": str(args.triangulation), "frames": results, "accepted_frames": accepted, "total_frames": len(results), "status": "bounded_ik_candidates_only", "allow_temporal": args.allow_temporal, "note": "No Blender rotations were written. Candidates require armature-space conversion and visual validation; temporal candidates remain provisional."}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(args.output), "accepted_frames": accepted, "total_frames": len(results)}, indent=2))


if __name__ == "__main__":
    main()
