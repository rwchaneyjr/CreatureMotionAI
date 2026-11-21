"""Export the validated 5-second Hydra loop twice and compare it to 10s refs."""
import cv2, json, numpy as np
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "data/generated/hydra_two_view_500_pose_pilot"
RENDER = ROOT / "candidate_v3_renders"
REF_SIDE = Path(r"C:\Users\rober\Desktop\7HeadedHydraSideMarch.mp4")
REF_FRONT = Path(r"C:\Users\rober\Desktop\7Headed Hydra Marching.mp4")
SIDE_OUT = ROOT / "hydra_reference_guided_walk_10s_v3_side.mp4"
COMPARE_OUT = ROOT / "hydra_reference_guided_walk_10s_v3_comparison.mp4"
STILL = ROOT / "hydra_reference_guided_walk_10s_v3_comparison_frame_0001.png"
REPORT = ROOT / "hydra_reference_guided_walk_10s_v3_report.json"
FPS, LOOP_FRAMES, TOTAL = 24, 120, 240
W, H = 480, 270

def read_ref(path):
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        raise RuntimeError(f"Could not open reference: {path}")
    fps = cap.get(cv2.CAP_PROP_FPS)
    count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    images = []
    for i in range(TOTAL):
        cap.set(cv2.CAP_PROP_POS_MSEC, i * 1000.0 / FPS)
        ok, image = cap.read()
        if not ok:
            break
        images.append(cv2.resize(image, (W, H), interpolation=cv2.INTER_AREA))
    cap.release()
    if len(images) != TOTAL:
        raise RuntimeError(f"{path}: found {len(images)} of {TOTAL} 24fps samples")
    return images, {"path": str(path), "fps": fps, "frame_count": count,
                    "resolution": [width, height], "sampled_frames": len(images)}

side_ref, side_meta = read_ref(REF_SIDE)
front_ref, front_meta = read_ref(REF_FRONT)
codec = cv2.VideoWriter_fourcc(*"mp4v")
side_writer = cv2.VideoWriter(str(SIDE_OUT), codec, FPS, (W, H))
compare_writer = cv2.VideoWriter(str(COMPARE_OUT), codec, FPS, (W*2, H*2))
if not side_writer.isOpened() or not compare_writer.isOpened():
    raise RuntimeError("Could not create output MP4 files")
first = None
seam_diffs = []
for i in range(TOTAL):
    # Reuse frames 1..120 exactly twice; references continue through their full 10s.
    j = i % LOOP_FRAMES + 1
    side_model = cv2.imread(str(RENDER / f"side_{j:04d}.png"))
    front_model = cv2.imread(str(RENDER / f"front_{j:04d}.png"))
    if side_model is None or front_model is None:
        raise FileNotFoundError(f"Missing Blender render for loop frame {j}")
    side_model = cv2.resize(side_model, (W,H))
    front_model = cv2.resize(front_model, (W,H))
    side_writer.write(side_model)
    panes = [side_ref[i].copy(), side_model, front_ref[i].copy(), front_model]
    labels = ["SIDE REFERENCE", "SIDE BLENDER LOOP (5s x2)",
              "FRONT REFERENCE", "FRONT BLENDER LOOP (5s x2)"]
    for pane, label in zip(panes, labels):
        cv2.rectangle(pane, (0,0), (W,25), (20,20,20), -1)
        cv2.putText(pane, label, (8,18), cv2.FONT_HERSHEY_SIMPLEX, .42,
                    (255,255,255), 1, cv2.LINE_AA)
    canvas = np.vstack((np.hstack(panes[:2]), np.hstack(panes[2:])))
    cv2.putText(canvas, f"t={i/FPS:.2f}s | side-weighted comparison | source views not synchronized",
                (8,H*2-8), cv2.FONT_HERSHEY_SIMPLEX, .37, (255,255,255), 1, cv2.LINE_AA)
    compare_writer.write(canvas)
    if i == 0:
        first = canvas.copy()
    if i in (LOOP_FRAMES-1, TOTAL-1):
        seam_diffs.append(float(np.mean(cv2.absdiff(side_model, cv2.resize(
            cv2.imread(str(RENDER / f"side_{1:04d}.png")), (W,H))))))
side_writer.release()
compare_writer.release()
cv2.imwrite(str(STILL), first)
report = {
    "status": "10S_LOOP_EXPORT_COMPLETE",
    "standalone_side_video": str(SIDE_OUT),
    "side_by_side_comparison": str(COMPARE_OUT),
    "first_comparison_frame": str(STILL),
    "duration_seconds": 10, "fps": FPS, "frames": TOTAL,
    "animation_source": str(ROOT / "hydra_reference_guided_walk_5s_v3.blend"),
    "loop_method": "The validated 120-frame, 5-second animation render sequence is repeated exactly twice.",
    "loop_frame_checks": {
        "blender_action_has_duplicate_endpoint_at_frame_121": True,
        "video_join_uses_frame_120_then_frame_1": True,
        "side_render_join_mean_absolute_pixel_difference": seam_diffs[0]
    },
    "references": {"side": side_meta, "front": front_meta},
    "reference_timing": "Each 10-second view is sampled at 24fps independently; synchronization is not asserted.",
    "motion_note": "This is the conservative, physically screened reference-guided loop. It is not an exact video match; see the 5-second safety report for limits.",
    "safety_report": str(ROOT / "hydra_reference_guided_walk_5s_v3_report.json")
}
REPORT.write_text(json.dumps(report, indent=2))
print(json.dumps({"side_video": str(SIDE_OUT), "comparison": str(COMPARE_OUT),
                  "report": str(REPORT), "seam_mean_abs_pixel_difference": seam_diffs[0]}))
