"""Prepare native Blender review stills from the selected video and track."""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from creature_motion_ai.reference_leg_identity import prepare_review


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("video", type=Path)
    parser.add_argument("track", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--frames", type=int, default=5)
    args = parser.parse_args()
    result = prepare_review(args.video, args.track, args.output_dir, frame_count=args.frames)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
