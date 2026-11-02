"""Select meaningful motion frames while preserving contact/event frames."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def point(frame: dict, name: str) -> tuple[float, float, float]:
    value = frame.get("landmarks", {}).get(name, [0.5, 0.5, 0.0])
    return tuple(float(x) for x in (value + [0.0, 0.0, 0.0])[:3])


def distance(a: dict, b: dict) -> float:
    names = ("motion_center", "motion_top", "motion_bottom")
    return sum(sum((x - y) ** 2 for x, y in zip(point(a, n), point(b, n))) ** 0.5 for n in names) / len(names)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("motion", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--min-gap", type=int, default=3)
    parser.add_argument("--motion-threshold", type=float, default=0.035)
    args = parser.parse_args()
    data = json.loads(args.motion.read_text(encoding="utf-8"))
    frames = data.get("frames", [])
    if not frames:
        raise ValueError("Motion file contains no frames")

    selected = [0]
    last = 0
    for i in range(1, len(frames) - 1):
        if i - last < args.min_gap:
            continue
        current = frames[i]
        event = bool(current.get("foot_contact_event") or current.get("contact_event") or current.get("phase_event"))
        changed = distance(frames[last], current) >= args.motion_threshold
        if event or changed:
            selected.append(i)
            last = i
    if len(frames) > 1 and selected[-1] != len(frames) - 1:
        selected.append(len(frames) - 1)

    result = {
        "source": str(args.motion),
        "source_frames": len(frames),
        "selected_frame_numbers": [int(frames[i].get("frame", i + 1)) for i in selected],
        "selected_indices": selected,
        "selected_count": len(selected),
        "min_gap": args.min_gap,
        "motion_threshold": args.motion_threshold,
        "note": "Use selected frames for pose fitting; interpolate between them and preserve explicit contact events.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
