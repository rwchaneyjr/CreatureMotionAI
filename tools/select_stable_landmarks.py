"""Select consistently tracked landmarks for a provisional diagnostic fit."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("quality", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--min-visible-rate", type=float, default=0.7)
    parser.add_argument("--min-confidence", type=float, default=0.1)
    args = parser.parse_args()
    data = json.loads(args.quality.read_text(encoding="utf-8"))
    selected = {}
    for name, item in data.get("landmarks", {}).items():
        keep = item.get("visible_rate", 0.0) >= args.min_visible_rate and item.get("mean_confidence", 0.0) >= args.min_confidence
        selected[name] = {"status": "provisional_stable" if keep else "needs_review", "visible_rate": item.get("visible_rate", 0.0), "mean_confidence": item.get("mean_confidence", 0.0)}
    kept = sum(x["status"] == "provisional_stable" for x in selected.values())
    result = {"source_quality_report": str(args.quality), "status": "provisional_only", "approval_rule": "Provisional stable landmarks are diagnostic only and cannot be exported as final animation labels.", "thresholds": {"min_visible_rate": args.min_visible_rate, "min_confidence": args.min_confidence}, "landmarks": selected}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(args.output), "provisional_stable": kept, "total": len(selected)}, indent=2))


if __name__ == "__main__":
    main()
