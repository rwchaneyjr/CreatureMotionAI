"""Create an explicit approval manifest for detector landmarks."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("quality", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    quality = json.loads(args.quality.read_text(encoding="utf-8"))
    landmarks = quality.get("landmarks", {})
    result = {
        "source_quality_report": str(args.quality),
        "status": "awaiting_review",
        "approval_rule": "Only landmarks with status approved may be used for triangulation.",
        "landmarks": {name: {"status": "needs_review", "correction": None} for name in sorted(landmarks)},
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(args.output), "landmarks": len(landmarks), "approved": 0}, indent=2))


if __name__ == "__main__":
    main()
