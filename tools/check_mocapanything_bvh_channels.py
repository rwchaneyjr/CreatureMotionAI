"""Report whether the generated BVH actually animates each leg joint."""
import argparse
import json
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("bvh")
parser.add_argument("--output")
args = parser.parse_args()
lines = Path(args.bvh).read_text(encoding="utf-8").splitlines()
motion_index = lines.index("MOTION")
columns = {}
current = None
column = 0
for line in lines[:motion_index]:
    parts = line.strip().split()
    if not parts:
        continue
    if parts[0] in ("ROOT", "JOINT"):
        current = parts[1]
    elif parts[0] == "CHANNELS":
        count = int(parts[1])
        columns[current] = list(range(column, column+count))
        column += count
frames = [list(map(float, line.split())) for line in lines[motion_index+3:] if line.strip()]
result = {}
for name, indices in columns.items():
    if not name.startswith("Leg_"):
        continue
    ranges = [max(row[i] for row in frames)-min(row[i] for row in frames) for i in indices]
    result[name] = {"channel_ranges": ranges, "all_rotation_channels_static": all(abs(v) < 1e-5 for v in ranges)}
report = {"frames": len(frames), "channels": column, "leg_channels": result,
          "static_leg_bones": [name for name, row in result.items() if row["all_rotation_channels_static"]]}
if args.output:
    Path(args.output).write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps({"frames": len(frames), "channels": column,
                  "static_leg_bones": len(report["static_leg_bones"]),
                  "report": args.output}, indent=2))
