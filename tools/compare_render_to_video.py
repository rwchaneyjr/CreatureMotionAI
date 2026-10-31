"""Compare Blender renders to matching MP4 frames and make a montage."""
import argparse, json
from pathlib import Path
import cv2
import numpy as np


def mask(image, reference=False):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    # Reference: dark creature on a light studio background. Workbench:
    # bright creature on a black background.
    _, m = cv2.threshold(gray, 150 if reference else 20, 255,
                         cv2.THRESH_BINARY_INV if reference else cv2.THRESH_BINARY)
    return cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))


def bbox(m):
    points = cv2.findNonZero(m)
    if points is None: return (0, 0, 1, 1)
    return cv2.boundingRect(points)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--video", required=True); p.add_argument("--render-dir", required=True)
    p.add_argument("--output", required=True); p.add_argument("--montage", required=True)
    args = p.parse_args()
    cap = cv2.VideoCapture(args.video); rows = []; scores = []
    for frame in (1, 12, 24):
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame - 1); ok, ref = cap.read()
        render_path = Path(args.render_dir) / f"blender_{frame:03d}.png"
        render = cv2.imread(str(render_path))
        if not ok or render is None: continue
        ref = cv2.resize(ref, (render.shape[1], render.shape[0]))
        rm, bm = mask(ref, reference=True), mask(render, reference=False)
        intersection = np.logical_and(rm > 0, bm > 0).sum()
        union = np.logical_or(rm > 0, bm > 0).sum()
        iou = float(intersection / max(union, 1))
        rx, ry, rw, rh = bbox(rm); bx, by, bw, bh = bbox(bm)
        centroid_error = float(np.hypot((rx + rw / 2) - (bx + bw / 2), (ry + rh / 2) - (by + bh / 2)) / max(render.shape[:2]))
        scale_error = float(abs((rw * rh) - (bw * bh)) / max(rw * rh, 1))
        scores.append({"frame": frame, "silhouette_iou": iou, "centroid_error": centroid_error, "scale_error": scale_error})
        ref_small = cv2.resize(ref, (render.shape[1] // 2, render.shape[0] // 2)); render_small = cv2.resize(render, (render.shape[1] // 2, render.shape[0] // 2))
        cv2.putText(ref_small, f"MP4 frame {frame}", (15, 30), cv2.FONT_HERSHEY_SIMPLEX, .8, (0, 255, 255), 2)
        cv2.putText(render_small, f"Blender frame {frame} IoU={iou:.3f}", (15, 30), cv2.FONT_HERSHEY_SIMPLEX, .65, (0, 255, 255), 2)
        rows.append(np.hstack([ref_small, render_small]))
    cap.release()
    montage = np.vstack(rows) if rows else np.zeros((10, 10, 3), np.uint8)
    Path(args.montage).parent.mkdir(parents=True, exist_ok=True); cv2.imwrite(args.montage, montage)
    report = {"frames": scores, "mean_silhouette_iou": float(np.mean([s["silhouette_iou"] for s in scores])) if scores else 0.0,
              "interpretation": "Higher IoU is better; silhouette comparison cannot resolve hidden legs or joint identity."}
    Path(args.output).write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report))


if __name__ == "__main__": main()
