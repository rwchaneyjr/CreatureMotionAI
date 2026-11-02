"""Build a safe one-second fit schedule from accepted geometry frames."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("geometry_report", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = json.loads(args.geometry_report.read_text(encoding="utf-8"))
    rows = report.get("frames", [])
    accepted = [i for i, row in enumerate(rows) if row.get("accepted_for_fit")]
    schedule = []
    for i, row in enumerate(rows):
        if i in accepted:
            mode = "pose_anchor"
        elif accepted:
            nearest = min(accepted, key=lambda j: abs(j - i))
            mode = "interpolate_from_anchor" if abs(nearest - i) <= 4 else "hold_rest_pose"
        else:
            nearest = None
            mode = "hold_rest_pose"
        schedule.append({"frame": row.get("frame"), "mode": mode, "geometry_failures": len(row.get("failures", []))})
    result = {"source_geometry_report": str(args.geometry_report), "frames": schedule, "anchor_count": len(accepted), "status": "conservative_one_second_schedule", "note": "Rejected frames are never forced into bone poses; they interpolate only across short gaps and otherwise hold the original rest pose."}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(args.output), "anchors": len(accepted), "frames": len(schedule)}, indent=2))


if __name__ == "__main__":
    main()
