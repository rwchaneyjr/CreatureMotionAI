"""Create a short diagnostic slice for the first one-second pose test."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--frames", type=int, default=24)
    args = parser.parse_args()
    data = json.loads(args.input.read_text(encoding="utf-8"))
    result = dict(data)
    result["frames"] = data.get("frames", [])[: args.frames]
    result["source_frame_count"] = len(data.get("frames", []))
    result["test_frame_count"] = len(result["frames"])
    result["status"] = "provisional_one_second_test"
    result["note"] = "Diagnostic only; provisional camera and landmarks are not final animation data."
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(args.output), "frames": len(result["frames"])}, indent=2))


if __name__ == "__main__":
    main()
