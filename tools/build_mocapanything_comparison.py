"""Build an honest 24-frame visual diagnostic; never labels a failed test as final."""
import argparse
import json
from pathlib import Path
import cv2
import numpy as np

parser = argparse.ArgumentParser()
parser.add_argument("--reference", required=True)
parser.add_argument("--renders", required=True)
parser.add_argument("--output", required=True)
parser.add_argument("--sheet", required=True)
parser.add_argument("--align-first-frame", action="store_true", help="Fixed 2D presentation alignment; no per-frame pose warp")
args = parser.parse_args()
reference = cv2.VideoCapture(args.reference)
if not reference.isOpened():
    raise RuntimeError(f"Cannot open reference: {args.reference}")
reference_fps = reference.get(cv2.CAP_PROP_FPS)
if abs(reference_fps - 24.0) > 0.1:
    raise RuntimeError(f"Expected 24 FPS reference, got {reference_fps}")
out = Path(args.output)
out.parent.mkdir(parents=True, exist_ok=True)
writer = cv2.VideoWriter(str(out), cv2.VideoWriter_fourcc(*"mp4v"), 24.0, (1280, 390))
if not writer.isOpened():
    raise RuntimeError(f"Cannot write {out}")
stills = {}
alignment = None
def creature_bounds(img):
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, (0, 55, 20), (179, 255, 255))
    points = cv2.findNonZero(mask)
    if points is None:
        raise RuntimeError("Cannot locate creature for presentation alignment")
    return cv2.boundingRect(points)
for frame in range(1, 25):
    ok, ref = reference.read()
    if not ok:
        raise RuntimeError(f"Reference missing frame {frame}")
    render = cv2.imread(str(Path(args.renders) / f"frame_{frame:04d}.png"))
    if render is None:
        raise RuntimeError(f"Blender render missing frame {frame}")
    ref = cv2.resize(ref, (640, 360), interpolation=cv2.INTER_AREA)
    render = cv2.resize(render, (640, 360), interpolation=cv2.INTER_AREA)
    if args.align_first_frame:
        if alignment is None:
            rx, ry, rw, rh = creature_bounds(ref)
            bx, by, bw, bh = creature_bounds(render)
            scale = rw / bw
            dx = (rx+rw/2) - scale*(bx+bw/2)
            dy = (ry+rh) - scale*(by+bh)
            alignment = np.float32([[scale, 0, dx], [0, scale, dy]])
        render = cv2.warpAffine(render, alignment, (640, 360), borderValue=(255,255,255))
    panel = np.full((390, 1280, 3), 235, np.uint8)
    panel[30:390, :640] = ref
    panel[30:390, 640:] = render
    cv2.putText(panel, f"Reference MP4 | frame {frame}", (12, 22), cv2.FONT_HERSHEY_SIMPLEX, .6, (0, 0, 0), 2)
    right_label = "Retarget | FAIL | fixed frame-1 alignment" if args.align_first_frame else "Original rig retarget | FAILED validation"
    cv2.putText(panel, right_label, (652, 22), cv2.FONT_HERSHEY_SIMPLEX, .6, (0, 0, 180), 2)
    writer.write(panel)
    if frame in (1, 6, 12, 18, 24):
        stills[frame] = panel.copy()
writer.release()
reference.release()
sheet = np.full((390*len(stills), 1280, 3), 235, np.uint8)
for i, (_, panel) in enumerate(stills.items()):
    sheet[390*i:390*(i+1)] = panel
cv2.imwrite(args.sheet, sheet)
print(json.dumps({"video": str(out), "contact_sheet": args.sheet, "frames": 24, "fps": 24,
                  "alignment": alignment.tolist() if alignment is not None else None,
                  "status": "DIAGNOSTIC_ONLY_MOTION_INVALID"}))
