"""Create a derived camera calibration at a video's panel resolution.

This preserves the source camera pose and scales the projection for image
coordinates. It calibrates presentation resolution, not unknown real-world
external-camera intrinsics.
"""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("calibration", type=Path)
    parser.add_argument("--width", type=int, required=True)
    parser.add_argument("--height", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    source = json.loads(args.calibration.read_text(encoding="utf-8"))
    old_w, old_h = source["resolution"]
    result = copy.deepcopy(source)
    result["source_calibration"] = str(args.calibration)
    result["resolution"] = [args.width, args.height]
    result["calibration_kind"] = "derived_image_resolution"
    result["external_intrinsics_known"] = False
    result["note"] = "Projection resized to the reference panel. Real external camera intrinsics still require calibration footage or Blender-generated matching views."
    sx, sy = args.width / old_w, args.height / old_h
    for camera in result.get("cameras", {}).values():
        projection = camera.get("projection_matrix")
        if projection and len(projection) >= 2:
            projection[0][0] *= sx
            projection[1][1] *= sy
        camera["image_resolution"] = [args.width, args.height]
        camera["image_scale_from_source"] = [sx, sy]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(args.output), "resolution": [args.width, args.height], "scale": [sx, sy], "external_intrinsics_known": False}, indent=2))


if __name__ == "__main__":
    main()
