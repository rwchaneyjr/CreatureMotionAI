"""Assemble Fly/Land MP4 previews and reference comparisons."""
from pathlib import Path
import json
import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/generated/dragon_quadruped_compatibility/fly_and_land"
REFERENCE = Path(r"C:\Users\rober\Downloads\Untitled video.mp4")
FPS = 24.0
COUNT = 120
PANEL = (800, 450)


def fit(frame, size=PANEL):
    w, h = size
    fh, fw = frame.shape[:2]
    scale = min(w / fw, h / fh)
    nw, nh = round(fw * scale), round(fh * scale)
    resized = cv2.resize(frame, (nw, nh), interpolation=cv2.INTER_AREA)
    canvas = np.zeros((h, w, 3), np.uint8)
    x, y = (w - nw) // 2, (h - nh) // 2
    canvas[y:y + nh, x:x + nw] = resized
    return canvas


def open_writer(path, size):
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), FPS, size)
    if not writer.isOpened():
        raise RuntimeError(f"Could not create video: {path}")
    return writer


def main():
    if not REFERENCE.is_file():
        raise FileNotFoundError(f"Reference video not found: {REFERENCE}")
    OUT.mkdir(parents=True, exist_ok=True)
    cap = cv2.VideoCapture(str(REFERENCE))
    if not cap.isOpened():
        raise RuntimeError(f"Cannot read reference video: {REFERENCE}")
    ref_fps = cap.get(cv2.CAP_PROP_FPS)
    ref_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    outputs = {}
    for action in ("Fly", "Land"):
        frames_dir = OUT / f"{action.lower()}_frames"
        paths = [frames_dir / f"frame_{i:04d}.png" for i in range(1, COUNT + 1)]
        missing = [p for p in paths if not p.is_file()]
        if missing:
            raise FileNotFoundError(f"Missing {action} render: {missing[0]}")
        preview_path = OUT / f"dragon_{action.lower()}_5sec.mp4"
        compare_path = OUT / f"dragon_{action.lower()}_reference_comparison.mp4"
        preview = open_writer(preview_path, PANEL)
        compare = open_writer(compare_path, (PANEL[0] * 2, PANEL[1] + 34))
        for i, path in enumerate(paths):
            render = cv2.imread(str(path), cv2.IMREAD_COLOR)
            if render is None:
                raise RuntimeError(f"Unreadable rendered frame: {path}")
            # Positive-X Blender view exposes the raised near wing but reverses
            # the creature's screen direction relative to the reference.
            render = cv2.flip(render, 1)
            render = fit(render)
            preview.write(render)
            source_index = min(round(i * ref_fps / FPS), ref_count - 1)
            cap.set(cv2.CAP_PROP_POS_FRAMES, source_index)
            ok, ref = cap.read()
            if not ok:
                raise RuntimeError(f"Could not decode reference frame {source_index}")
            ref = fit(ref)
            row = np.zeros((PANEL[1] + 34, PANEL[0] * 2, 3), np.uint8)
            cv2.putText(row, f"REFERENCE | {REFERENCE.name}", (16, 24), cv2.FONT_HERSHEY_SIMPLEX, .52, (245, 245, 245), 1, cv2.LINE_AA)
            label = "FLY | held raised-wing airborne pose" if action == "Fly" else "LAND | authored transition to existing Idle"
            cv2.putText(row, label, (PANEL[0] + 16, 24), cv2.FONT_HERSHEY_SIMPLEX, .48, (245, 245, 245), 1, cv2.LINE_AA)
            row[34:, :PANEL[0]] = ref
            row[34:, PANEL[0]:] = render
            compare.write(row)
        preview.release()
        compare.release()
        outputs[action] = {"preview": str(preview_path), "comparison": str(compare_path)}

    cap.release()
    checks = {}
    for label, path in [(k + "_preview", Path(v["preview"])) for k, v in outputs.items()] + [(k + "_comparison", Path(v["comparison"])) for k, v in outputs.items()]:
        video = cv2.VideoCapture(str(path))
        checks[label] = {"opened": bool(video.isOpened()), "fps": video.get(cv2.CAP_PROP_FPS), "frames": int(video.get(cv2.CAP_PROP_FRAME_COUNT)), "size": [int(video.get(cv2.CAP_PROP_FRAME_WIDTH)), int(video.get(cv2.CAP_PROP_FRAME_HEIGHT))]}
        video.release()
        if not checks[label]["opened"] or checks[label]["frames"] != COUNT:
            raise RuntimeError(f"Video verification failed for {label}: {checks[label]}")
    report_path = OUT / "fly_land_preview_report.json"
    report = {
        "status": "VIDEOS_ENCODED_VISUAL_REVIEW_REQUIRED",
        "reference": str(REFERENCE),
        "reference_fps": ref_fps,
        "reference_frame_count": ref_count,
        "outputs": outputs,
        "fps": FPS,
        "frames": COUNT,
        "seconds": COUNT / FPS,
        "camera_note": "Rendered from the side that shows the raised wing; candidate panel horizontally flipped to match reference head/tail direction.",
        "validation": "Video streams reopened and frame counts verified. Visual similarity and physical landing validity require human review.",
        "checks": checks,
    }
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"report": str(report_path), "outputs": outputs, "checks": checks}, indent=2))


if __name__ == "__main__":
    main()
