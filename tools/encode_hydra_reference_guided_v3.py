import cv2, json, numpy as np
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "data/generated/hydra_two_view_500_pose_pilot"
RENDER = ROOT / "candidate_v3_renders"
REF_SIDE = Path(r"C:\Users\rober\Desktop\7HeadedHydraSideMarch.mp4")
REF_FRONT = Path(r"C:\Users\rober\Desktop\7Headed Hydra Marching.mp4")
OUT = ROOT / "hydra_reference_guided_walk_5s_v3_comparison.mp4"
STILL = ROOT / "hydra_reference_guided_walk_5s_v3_comparison_frame_0001.png"
REPORT = ROOT / "hydra_reference_guided_walk_5s_v3_comparison_report.json"
W, H, FPS, N = 480, 270, 24, 120

def read_clip(path):
    if not path.exists():
        raise FileNotFoundError(path)
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        raise RuntimeError(f"Cannot read {path}")
    source_fps = cap.get(cv2.CAP_PROP_FPS)
    count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    frames = []
    for i in range(N):
        # Sample by timestamp so each source is handled at the comparison's 24 fps.
        cap.set(cv2.CAP_PROP_POS_MSEC, i * 1000.0 / FPS)
        ok, image = cap.read()
        if not ok:
            break
        frames.append(cv2.resize(image, (W, H), interpolation=cv2.INTER_AREA))
    cap.release()
    if len(frames) != N:
        raise RuntimeError(f"{path} provided {len(frames)} of {N} requested samples")
    return frames, {"path": str(path), "fps": source_fps, "frame_count": count,
                    "resolution": [width, height], "sampled_frames": len(frames)}

side_ref, side_meta = read_clip(REF_SIDE)
front_ref, front_meta = read_clip(REF_FRONT)
fourcc = cv2.VideoWriter_fourcc(*"mp4v")
writer = cv2.VideoWriter(str(OUT), fourcc, FPS, (W * 2, H * 2))
if not writer.isOpened():
    raise RuntimeError("Could not open MP4 writer")
first = None
for i in range(N):
    side_render = cv2.imread(str(RENDER / f"side_{i+1:04d}.png"))
    front_render = cv2.imread(str(RENDER / f"front_{i+1:04d}.png"))
    if side_render is None or front_render is None:
        raise FileNotFoundError(f"Missing Blender render for frame {i+1}")
    side_render = cv2.resize(side_render, (W, H))
    front_render = cv2.resize(front_render, (W, H))
    panes = [side_ref[i].copy(), side_render, front_ref[i].copy(), front_render]
    labels = ["SIDE REFERENCE", "SIDE BLENDER V3", "FRONT REFERENCE", "FRONT BLENDER V3"]
    for pane, label in zip(panes, labels):
        cv2.rectangle(pane, (0, 0), (W, 25), (20, 20, 20), -1)
        cv2.putText(pane, label, (8, 18), cv2.FONT_HERSHEY_SIMPLEX, .48,
                    (255, 255, 255), 1, cv2.LINE_AA)
    canvas = np.vstack((np.hstack(panes[:2]), np.hstack(panes[2:])))
    cv2.putText(canvas, f"t={i/FPS:.2f}s | side-weighted reference-guided loop | source views sampled independently",
                (8, H*2-8), cv2.FONT_HERSHEY_SIMPLEX, .39, (255,255,255), 1, cv2.LINE_AA)
    writer.write(canvas)
    if i == 0:
        first = canvas.copy()
writer.release()
cv2.imwrite(str(STILL), first)
report = {
    "status": "RENDERED_VISUAL_REVIEW_REQUIRED",
    "comparison_video": str(OUT), "first_frame_still": str(STILL),
    "duration_seconds": 5, "fps": FPS, "panel_resolution": [W,H],
    "output_resolution": [W*2,H*2],
    "source_videos": {"side": side_meta, "front": front_meta},
    "sampling": "Both reference clips sampled independently at 24 fps; they are not assumed synchronized.",
    "animation": "Conservative 2-leg in-place gait offsets layered on the existing extrema-timed Hydra action; not mocap or pixel-fitted.",
    "visual_similarity": "Not scored; visual review required. Camera framing is approximate and source clips may have different framing.",
    "validation_report": str(ROOT / "hydra_reference_guided_walk_5s_v3_report.json")
}
REPORT.write_text(json.dumps(report, indent=2))
print(json.dumps({"video": str(OUT), "still": str(STILL), "report": str(REPORT)}))
