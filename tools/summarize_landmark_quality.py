"""Summarize visibility and confidence quality for two-view landmark proposals."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("proposals", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    data = json.loads(args.proposals.read_text(encoding="utf-8"))
    stats = {}
    for row in data.get("frames", []):
        for camera in ("camera_A", "camera_B"):
            for name, item in row.get(camera, {}).get("landmarks", {}).items():
                s = stats.setdefault(name, {"observations": 0, "visible": 0, "confidence_sum": 0.0, "uncertain": 0})
                s["observations"] += 1
                s["visible"] += int(bool(item.get("visible")))
                s["uncertain"] += int(item.get("state", "").startswith("uncertain"))
                s["confidence_sum"] += float(item.get("confidence", 0.0))
    for name, s in stats.items():
        s["visible_rate"] = s["visible"] / max(s["observations"], 1)
        s["mean_confidence"] = s["confidence_sum"] / max(s["observations"], 1)
        del s["confidence_sum"]
    ranked = sorted(stats.items(), key=lambda kv: (kv[1]["visible_rate"], kv[1]["mean_confidence"]))
    result = {"source": str(args.proposals), "landmarks": stats, "lowest_quality_first": [{"name": n, **s} for n, s in ranked], "note": "Low-quality landmarks require review and must not drive triangulation automatically."}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(args.output), "landmarks": len(stats), "lowest_quality": [{"name": n, "visible_rate": s["visible_rate"]} for n, s in ranked[:10]]}, indent=2))


if __name__ == "__main__":
    main()
