"""CLI entry point for conservative reviewed 2D step-event analysis."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ADDON_ROOT = Path(__file__).resolve().parent.parent
if str(ADDON_ROOT) not in sys.path:
    sys.path.insert(0, str(ADDON_ROOT))

from creature_motion_ai.reference_step_events import analyze_reference_step_track


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("track", type=Path)
    parser.add_argument("report", type=Path)
    parser.add_argument("--approval", type=Path)
    args = parser.parse_args()
    track = json.loads(args.track.read_text(encoding="utf-8-sig"))
    report = analyze_reference_step_track(track, args.track, args.approval)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"report": str(args.report), "status": report["status"],
                      "frames": report["frames_total"],
                      "reviewed_frames": report["frames_with_reviewed_hip_knee_foot"],
                      "eligible_for_3d_fit": report["eligible_for_3d_fit"],
                      "animation_use_allowed": report["animation_use_allowed"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
