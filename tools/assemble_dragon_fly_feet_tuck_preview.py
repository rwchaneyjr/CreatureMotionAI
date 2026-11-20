"""Encode the five-second Fly Feet Tuck render and a reference comparison."""
from pathlib import Path
import json
import argparse

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/generated/dragon_quadruped_compatibility/fly_and_land"
REFERENCE = Path(r"C:\Users\rober\Desktop\dragon fly feet tucked !~.mp4")
FPS = 24
COUNT = 120
PANEL = (800, 450)


def fit(image):
    w, h = PANEL
    ih, iw = image.shape[:2]
    scale = min(w / iw, h / ih)
    rw, rh = round(iw * scale), round(ih * scale)
    resized = cv2.resize(image, (rw, rh), interpolation=cv2.INTER_AREA)
    canvas = np.zeros((h, w, 3), np.uint8)
    x, y = (w - rw) // 2, (h - rh) // 2
    canvas[y:y + rh, x:x + rw] = resized
    return canvas


def writer(path, size):
    obj = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), FPS, size)
    if not obj.isOpened():
        raise RuntimeError(f"Cannot create {path}")
    return obj


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--variant", default="", help="Optional filename suffix, e.g. rear_fold_back")
    parser.add_argument("--animation-note", default="Wing timing comes from the existing FLAP Action. Four leg chains use the tucked pose sampled from existing RUN frame 30; no per-frame leg mocap was claimed.")
    args = parser.parse_args()
    suffix = f"_{args.variant}" if args.variant else ""
    if not REFERENCE.is_file():
        raise FileNotFoundError(REFERENCE)
    cap = cv2.VideoCapture(str(REFERENCE))
    if not cap.isOpened():
        raise RuntimeError(f"Cannot read {REFERENCE}")
    ref_fps = cap.get(cv2.CAP_PROP_FPS)
    ref_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    if ref_count < COUNT:
        raise RuntimeError("Reference does not contain five seconds at the selected rate")
    frame_dir = OUT / f"fly_feet_tuck{suffix}_frames"
    preview_path = OUT / f"dragon_fly_feet_tuck{suffix}_5sec.mp4"
    compare_path = OUT / f"dragon_fly_feet_tuck{suffix}_comparison.mp4"
    preview = writer(preview_path, PANEL)
    compare = writer(compare_path, (PANEL[0] * 2, PANEL[1] + 36))
    samples = []
    for i in range(COUNT):
        image_path = frame_dir / f"frame_{i+1:04d}.png"
        render = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
        if render is None:
            raise FileNotFoundError(image_path)
        render = fit(cv2.flip(render, 1))
        preview.write(render)
        cap.set(cv2.CAP_PROP_POS_FRAMES, min(round(i * ref_fps / FPS), ref_count - 1))
        ok, ref = cap.read()
        if not ok:
            raise RuntimeError(f"Cannot decode reference frame {i+1}")
        ref = fit(ref)
        row = np.zeros((PANEL[1] + 36, PANEL[0] * 2, 3), np.uint8)
        cv2.putText(row, "REFERENCE | dragon fly feet tucked", (12, 25), cv2.FONT_HERSHEY_SIMPLEX, .52, (255,255,255), 1, cv2.LINE_AA)
        cv2.putText(row, "CREATUREMOTIONAI | FLAP timing + tucked leg pose", (PANEL[0]+12, 25), cv2.FONT_HERSHEY_SIMPLEX, .47, (255,255,255), 1, cv2.LINE_AA)
        row[36:, :PANEL[0]] = ref
        row[36:, PANEL[0]:] = render
        compare.write(row)
        if i in (0, 23, 47, 71, 95, 119):
            tile = cv2.resize(render, (480,270))
            cv2.putText(tile, f"frame {i+1}", (10,24), cv2.FONT_HERSHEY_SIMPLEX,.7,(255,255,255),2,cv2.LINE_AA)
            samples.append(tile)
    cap.release(); preview.release(); compare.release()
    contact = np.vstack([np.hstack(samples[:3]), np.hstack(samples[3:])])
    cv2.imwrite(str(OUT / f"dragon_fly_feet_tuck{suffix}_contact_sheet.png"), contact)
    checks = {}
    for name, path in (("preview",preview_path),("comparison",compare_path)):
        c = cv2.VideoCapture(str(path))
        checks[name] = {"opened":bool(c.isOpened()),"fps":c.get(cv2.CAP_PROP_FPS),"frames":int(c.get(cv2.CAP_PROP_FRAME_COUNT)),"size":[int(c.get(cv2.CAP_PROP_FRAME_WIDTH)),int(c.get(cv2.CAP_PROP_FRAME_HEIGHT))]}
        c.release()
        if not checks[name]["opened"] or checks[name]["frames"] != COUNT:
            raise RuntimeError(f"Video verification failed: {name} {checks[name]}")
    report = {"status":"VIDEOS_ENCODED_VISUAL_REVIEW_REQUIRED","reference":str(REFERENCE),"reference_fps":ref_fps,"preview":str(preview_path),"comparison":str(compare_path),"duration_seconds":5,"fps":FPS,"frames":COUNT,"checks":checks,"animation_note":args.animation_note}
    (OUT / f"dragon_fly_feet_tuck{suffix}_preview_report.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    print(json.dumps(report,indent=2))


if __name__ == "__main__": main()
