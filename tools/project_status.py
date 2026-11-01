"""Show CreatureMotionAI pipeline readiness without changing project files."""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def exists(relative: str) -> bool:
    return (ROOT / relative).exists()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference", type=Path, help="Optional synchronized split-screen MP4")
    args = parser.parse_args()

    checks = {
        "original_static_standing": exists("data/generated/original_static_standing.blend"),
        "two_camera_calibration": exists("data/generated/two_camera_studio/camera_calibration.json"),
        "synthetic_dataset_validation": exists("data/generated/synthetic_balisk_100_occlusion/validation_report.json"),
        "detector_exam": exists("data/generated/synthetic_detector_exam.json"),
        "opencv_importable": importlib.util.find_spec("cv2") is not None,
        "dual_camera_preparer": exists("tools/prepare_dual_camera_reference.py"),
    }
    result = {
        "project": str(ROOT),
        "checks": checks,
        "reference_supplied": bool(args.reference),
        "reference_exists": bool(args.reference and args.reference.exists()),
        "safe_next_stage": "provide a synchronized split-screen MP4" if not args.reference else "run dual-camera preparation gate",
        "ready_for_external_pose_fitting": False,
        "note": "External fitting remains blocked until a synchronized two-view reference passes validation.",
    }
    if args.reference and args.reference.exists():
        result["safe_next_stage"] = "python tools/prepare_dual_camera_reference.py ..."
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
