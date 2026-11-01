"""Prepare a split-screen reference for later pose fitting.

This command intentionally stops at validation. It never triangulates or edits
Blender files until both panels pass the input-quality gate.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from import_dual_camera_reference import split_video
from validate_dual_camera_reference import validate


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    split_report = split_video(args.input, args.output_dir)
    consistency = validate(args.input)
    report = {
        "input": str(args.input),
        "split_report": split_report,
        "consistency_report": consistency,
        "ready_for_pose_fitting": bool(
            split_report["valid"] and consistency["ready_for_triangulation"]
        ),
        "next_stage": (
            "calibrated two-view pose fitting"
            if split_report["valid"] and consistency["ready_for_triangulation"]
            else "review or replace the reference video"
        ),
    }
    output = args.output_dir / "dual_camera_preparation_report.json"
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    if not report["ready_for_pose_fitting"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
