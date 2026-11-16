from pathlib import Path
import json, hashlib
import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
VIDEO = Path(r"C:\Users\rober\Downloads\2VIEWSBALISK SYNCWALK.mp4")
APPROVED = ROOT / "data/generated/frontL_selected_video_landmarks.json"
RAW = ROOT / "data/generated/selected_video_dlc_frontL_predictions.json"
OUT = ROOT / "data/generated/dlc_audit_20261116"
OUT.mkdir(parents=True, exist_ok=True)
FRAME = 1

def sha256(p):
    h = hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()

approved = json.loads(APPROVED.read_text(encoding="utf-8"))
raw = json.loads(RAW.read_text(encoding="utf-8"))
raw_frame = next(x for x in raw["frames"] if int(x["frame"]) == FRAME)
ap = approved["landmarks"][str(FRAME)]
names = ["hip", "knee", "ankle", "foot"]

cap = cv2.VideoCapture(str(VIDEO))
cap.set(cv2.CAP_PROP_POS_FRAMES, FRAME - 1)
ok, full = cap.read()
cap.release()
if not ok:
    raise RuntimeError(f"Could not read frame {FRAME} from {VIDEO}")

# The approved JSON and selected-video predictions are panel coordinates from
# the left 640x720 side panel of the split reference. The training config has
# a different crop (y=277..624) for its own copied video; do not apply that
# offset when drawing this approved-vs-raw audit.
x0, y0, x1, y1 = 0, 0, 640, 720
crop = full[y0:y1, x0:x1].copy()
if crop.shape[1] != 640 or crop.shape[0] != 720:
    raise RuntimeError(f"Unexpected crop shape: {crop.shape}")

approved_pts = {n: (float(ap[n]["x"]), float(ap[n]["y"])) for n in names}
raw_pts = {n: tuple(map(float, raw_frame["landmarks_2d"][n])) for n in names}
errors = {}
for n in names:
    errors[n] = {"approved": list(approved_pts[n]), "raw": list(raw_pts[n]), "dx": raw_pts[n][0] - approved_pts[n][0], "dy": raw_pts[n][1] - approved_pts[n][1], "distance_px": float(np.linalg.norm(np.subtract(raw_pts[n], approved_pts[n]))), "raw_confidence": float(raw_frame["confidence"][n]), "approved_status": ap[n]["approval"]}

def draw_points(im, pts, color, prefix, connect=True):
    out = im.copy()
    if connect:
        for a, b in zip(names, names[1:]):
            cv2.line(out, tuple(map(int, pts[a])), tuple(map(int, pts[b])), color, 2, cv2.LINE_AA)
    for i, n in enumerate(names, 1):
        p = tuple(map(int, pts[n]))
        cv2.circle(out, p, 7, color, -1, cv2.LINE_AA)
        cv2.putText(out, f"{prefix}{i} {n}", (p[0] + 8, p[1] - 5), cv2.FONT_HERSHEY_SIMPLEX, .43, color, 1, cv2.LINE_AA)
    return out

approved_img = draw_points(crop, approved_pts, (0, 210, 0), "A", True)
raw_img = draw_points(crop, raw_pts, (0, 0, 255), "R", True)
overlay = crop.copy()
for n in names:
    a, r = tuple(map(int, approved_pts[n])), tuple(map(int, raw_pts[n]))
    cv2.line(overlay, a, r, (0, 220, 255), 1, cv2.LINE_AA)
overlay = draw_points(overlay, approved_pts, (0, 210, 0), "A", False)
overlay = draw_points(overlay, raw_pts, (0, 0, 255), "R", False)

legend = "GREEN approved | RED raw DLC | YELLOW error | frame 1 | identity UNVERIFIED"
for im in (approved_img, raw_img, overlay):
    cv2.rectangle(im, (0, 0), (im.shape[1], 25), (35, 35, 35), -1)
    cv2.putText(im, legend, (7, 17), cv2.FONT_HERSHEY_SIMPLEX, .42, (240, 240, 240), 1, cv2.LINE_AA)
sheet = np.hstack([approved_img, raw_img, overlay])
image_path = OUT / "frame_001_approved_vs_raw_dlc.png"
cv2.imwrite(str(image_path), sheet)

report = {"status": "AUDITED_RAW_VS_APPROVED", "frame": FRAME, "source_video": str(VIDEO), "source_video_sha256": sha256(VIDEO), "video_dimensions": {"width": int(full.shape[1]), "height": int(full.shape[0])}, "dlc_coordinate_system": {"approved_and_selected_prediction_panel": {"crop_x": [0, 640], "crop_y": [0, 720], "width": 640, "height": 720, "transform": "identity within left side panel"}, "training_config_crop": {"crop_x": [0, 640], "crop_y": [277, 624], "width": 640, "height": 347, "transform": "different project-local video crop; not applied here"}}, "training_config": str(ROOT / "data/deeplabcut/CreatureMotionAI-CreatureMotionAI-2026-10-29/config.yaml"), "training_video_declared_by_config": str(ROOT / "data/deeplabcut/CreatureMotionAI-CreatureMotionAI-2026-10-29/videos/balisk.mp4"), "checkpoint": str(ROOT / "data/generated/dlc_balisk_project/BaliskDLC-CreatureMotionAI-2026-11-03/dlc-models-pytorch/iteration-0/BaliskDLCNov3-trainset95shuffle1/train/snapshot-best-030.pt"), "approved_file": str(APPROVED), "approved_source_video_declared": approved.get("source_video"), "approved_identity": approved.get("identity"), "approved_identity_confirmation": approved.get("identity_confirmation"), "raw_prediction_file": str(RAW), "raw_prediction_metadata": {"source": raw_frame.get("source"), "leg": raw_frame.get("leg"), "status": raw_frame.get("status")}, "points": errors, "mean_error_px": float(np.mean([v["distance_px"] for v in errors.values()])), "findings": {"A_incorrect_original_labels": "NOT_PROVEN: approved points are recorded as manually approved, but physical identity is explicitly USER_REQUIRED.", "B_incorrect_model_predictions": "POSSIBLE: raw DLC is close at hip/ankle/foot but knee confidence is 0.820; frame 1 alone does not prove prediction failure.", "C_wrong_video_or_coordinate_mapping": "CONFIRMED: the first overlay used the training crop offset on left-panel coordinates. The approved source is 2VIEWSBALISK SYNCWALK.mp4, while the training config declares project-local balisk.mp4.", "D_incorrect_landmark_to_leg_mapping": "CONFIRMED_UNVERIFIED: file labels the chain Front.L but identity_confirmation is USER_REQUIRED; no automatic physical identity proof exists.", "E_incorrect_overlay_drawing": "CONTRIBUTING: applying the wrong crop offset displaced the first audit points; the prior green chain also connected unverified labels as one physical leg."}, "smallest_correction": "Use left-panel 640x720 coordinates for this audit, keep approved and raw points visually separate, and do not optimize Blender from this chain until physical identity is verified."}
(OUT / "audit_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
print(image_path)
print(OUT / "audit_report.json")
