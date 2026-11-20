"""Create a conservative report of one side-view leg's candidate step events."""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from creature_motion_ai.reference_step_events import analyze_reference_step_track


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("track", type=Path, help="JSON hip/knee/foot track")
    parser.add_argument("output", type=Path, help="Output report JSON")
    parser.add_argument("--approval", type=Path, help="Hash-bound manual identity approval manifest")
    args = parser.parse_args()
    track_path = args.track.resolve()
    track = json.loads(track_path.read_text(encoding="utf-8-sig"))
    report = analyze_reference_step_track(track, track_path, args.approval.resolve() if args.approval else None)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({key: report[key] for key in (
        "leg", "status", "animation_use_allowed", "frames_total",
        "frames_with_reviewed_hip_knee_foot", "frames_candidate_only",
        "candidate_lift_excursion_px", "blockers", "source_track_sha256")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
