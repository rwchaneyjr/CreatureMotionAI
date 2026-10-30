"""Validate a normalized motion JSON file without requiring Blender."""
import argparse
import json
from pathlib import Path

from creature_motion_ai.motion_data import validate_frame


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("motion", type=Path)
    args = parser.parse_args()
    data = json.loads(args.motion.read_text(encoding="utf-8"))
    frames = data.get("frames", data if isinstance(data, list) else [])
    for frame in frames:
        validate_frame(frame)
    print(f"Validated {len(frames)} frames")


if __name__ == "__main__":
    main()
