"""Check whether a landmark package is safe to send to Blender pose fitting."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("triangulation", type=Path)
    parser.add_argument("validation", type=Path)
    parser.add_argument("calibration", type=Path)
    parser.add_argument("approval", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    tri, validation, calibration, approval = map(load, (args.triangulation, args.validation, args.calibration, args.approval))
    checks = {
        "triangulation_structurally_valid": bool(validation.get("invalid_points", 1) == 0 and validation.get("accepted_frames", 0) > 0),
        "camera_calibration_final": not bool(calibration.get("provisional", False)),
        "landmarks_explicitly_approved": approval.get("status") == "reviewed" and any(x.get("status") == "approved" for x in approval.get("landmarks", {}).values()),
        "triangulation_not_provisional": tri.get("status") not in ("provisional", "provisional_one_second_test"),
    }
    result = {"checks": checks, "ready_for_pose_fit": all(checks.values()), "note": "Provisional diagnostics are intentionally blocked from changing the armature."}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
