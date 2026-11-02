"""Create the explicit Balisk landmark-to-original-bone mapping."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


LEG_ROOTS = [
    "Leg_Front.L", "Leg_Front.R", "Leg_MidFront.L", "Leg_MidFront.R",
    "Leg_MidRear.L", "Leg_MidRear.R", "Leg_Rear.L", "Leg_Rear.R",
]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    legs = {}
    for root in LEG_ROOTS:
        legs[root] = {"hip": f"{root}_01", "knee": f"{root}_02", "foot": f"{root}_03", "landmarks": [f"{root}_01_head", f"{root}_02_head", f"{root}_03_tail"]}
    result = {
        "source": "original_static_standing.blend",
        "armature_bone_count": 38,
        "body": {"root": "Root", "body": ["Body_01", "Body_02", "Body_03"], "head": ["Head_01", "Head_02"], "tail": [f"Tail_{i:02d}" for i in range(1, 9)]},
        "legs": legs,
        "note": "Names preserve the original armature; no replacement skeleton is introduced.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(args.output), "legs": len(legs), "armature_bone_count": 38}, indent=2))


if __name__ == "__main__":
    main()
