"""Create a sparse motion file from an adaptive keyframe plan."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("motion", type=Path)
    parser.add_argument("plan", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    motion = json.loads(args.motion.read_text(encoding="utf-8"))
    plan = json.loads(args.plan.read_text(encoding="utf-8"))
    frames = motion.get("frames", [])
    indices = plan.get("selected_indices", [])
    if not frames or not indices:
        raise ValueError("Motion or adaptive plan is empty")
    selected = [frames[i] for i in indices if 0 <= int(i) < len(frames)]
    result = dict(motion)
    result["frames"] = selected
    result["source_frame_count"] = len(frames)
    result["sparse_frame_count"] = len(selected)
    result["adaptive_keyframe_plan"] = str(args.plan)
    result["preserve_source_frame_numbers"] = True
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(args.output), "source_frames": len(frames), "sparse_frames": len(selected), "frames": [f.get("frame") for f in selected]}, indent=2))


if __name__ == "__main__":
    main()
