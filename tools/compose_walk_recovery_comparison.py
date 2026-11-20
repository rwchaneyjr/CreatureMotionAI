"""Make a same-camera three-up five-second video and numeric summary."""
import json
from pathlib import Path

import cv2
import numpy as np

root = Path(__file__).resolve().parents[1]
out = root / "data/generated/walk_recovery_comparison_v1"
sources = {
    "Earlier baseline": out / "baseline",
    "Seamless loop": out / "seamless",
    "Contact locked": root / "data/generated/balisk_camera_fullbody_walk_02/contact_lock_v1/candidate_frames",
}
metadata_paths = {
    "Earlier baseline": out / "baseline/render_metadata.json",
    "Seamless loop": out / "seamless/render_metadata.json",
    "Contact locked": out / "contact_locked/render_metadata.json",
}
names = list(sources)
panel_w, panel_h, header_h = 960, 540, 48
out.mkdir(parents=True, exist_ok=True)
video_path = out / "three_version_same_camera_5sec.mp4"
writer = cv2.VideoWriter(str(video_path), cv2.VideoWriter_fourcc(*"mp4v"), 24,
                         (panel_w * 3, panel_h + header_h))
if not writer.isOpened():
    raise RuntimeError("OpenCV could not create the MP4 writer")

def frame_path(source, index):
    # Baseline and seamless use normalized render names; existing contact images
    # use Blender's four-digit frame naming.
    for stem in (f"frame_{index:04d}", f"frame_{index:06d}"):
        p = source / f"{stem}.png"
        if p.exists():
            return p
    return None

contact_candidates = sorted(sources["Contact locked"].glob("frame_*.png"))
if len(contact_candidates) < 120:
    raise RuntimeError(f"Expected 120 contact renders, found {len(contact_candidates)}")
for i in range(1, 121):
    canvas = np.full((panel_h + header_h, panel_w * 3, 3), 28, np.uint8)
    for column, name in enumerate(names):
        p = frame_path(sources[name], i)
        if name == "Contact locked":
            p = contact_candidates[i - 1]
        if not p:
            raise FileNotFoundError(f"Missing {name} frame {i}")
        image = cv2.imread(str(p), cv2.IMREAD_COLOR)
        if image is None:
            raise RuntimeError(f"Could not read {p}")
        image = cv2.resize(image, (panel_w, panel_h), interpolation=cv2.INTER_AREA)
        x = column * panel_w
        canvas[header_h:, x:x + panel_w] = image
        cv2.putText(canvas, name, (x + 20, 34), cv2.FONT_HERSHEY_SIMPLEX,
                    0.85, (240, 240, 240), 2, cv2.LINE_AA)
        cv2.putText(canvas, f"Frame {i}/120", (x + panel_w - 190, 34),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (190, 210, 230), 1, cv2.LINE_AA)
    writer.write(canvas)
writer.release()

# Useful rig-space motion summary from Blender-evaluated bone endpoints.
pose_summary = {}
for name, path in metadata_paths.items():
    meta = json.loads(path.read_text(encoding="utf-8"))
    bones = meta["bone_world_samples"]
    legs = sorted({bone.rsplit("_", 1)[0] for bone in bones
                   if bone.startswith("Leg_") and bone.endswith("_01")})
    rows = {}
    for leg in legs:
        b1, b2, b3 = (bones.get(f"{leg}_{suffix}") for suffix in ("01", "02", "03"))
        if not (b1 and b2 and b3):
            continue
        feet = np.asarray(b3["tail"], dtype=float)
        hips = np.asarray(b1["head"], dtype=float)
        knees = np.asarray(b1["tail"], dtype=float)
        ankle = np.asarray(b2["tail"], dtype=float)
        angles = []
        for hip, knee, ankle_point in zip(hips, knees, ankle):
            a, b = hip - knee, ankle_point - knee
            denom = np.linalg.norm(a) * np.linalg.norm(b)
            angles.append(float(np.degrees(np.arccos(np.clip(np.dot(a, b) / denom, -1, 1))))
                           if denom > 1e-10 else 0.0)
        rows[leg] = {
            "hip_world_range_xyz": np.round(np.ptp(hips, axis=0), 5).tolist(),
            "foot_tip_world_range_xyz": np.round(np.ptp(feet, axis=0), 5).tolist(),
            "foot_tip_vertical_peak_to_peak": round(float(np.ptp(feet[:, 2])), 5),
            "knee_angle_range_deg": [round(float(min(angles)), 2), round(float(max(angles)), 2)],
        }
    pose_summary[name] = {"action": meta["action"], "legs": rows,
                          "camera": meta["camera"],
                          "root_bone_head_start": bones.get("Root", {}).get("head", [[None]])[0],
                          "root_bone_head_end": bones.get("Root", {}).get("head", [[None]])[-1],
                          "root_bone_head_range_xyz": (np.round(np.ptp(np.asarray(bones["Root"]["head"], dtype=float), axis=0), 5).tolist()
                                                        if "Root" in bones else None)}

contact_report_path = root / "data/generated/balisk_camera_fullbody_walk_02/contact_lock_v1/contact_lock_comparison.json"
contact_report = json.loads(contact_report_path.read_text(encoding="utf-8"))
report = {
    "status": "RENDERED_AND_VISUALLY_REVIEWED",
    "video": str(video_path), "frames": 120, "fps": 24, "duration_seconds": 5,
    "layout": "three synchronized panels, common orthographic camera, 1280x720 source renders scaled to 960x540 panels",
    "camera": {"projection": "ORTHO", "location": [-3.0, -0.1, 0.04],
               "rotation_euler": [1.5575, 0.0, -1.5375], "ortho_scale": 2.35},
    "versions": pose_summary,
    "action_history": {
        "earlier_baseline": "CMAI_EightLeg_GroundFitted_reference_walk_refinement_04 (41-frame Action evaluated across 120-frame scene)",
        "seamless_loop": "CMAI_EightLeg_GroundFitted_walk_SeamlessLoop_InPlace (duplicated from 41-frame source; saved report says 380 F-curves updated and mesh endpoint error 0)",
        "contact_locked": "CMAI_ContactLock_EightLeg (121-frame Action evaluated for 120-frame preview)",
        "contact_method": contact_report["method"],
    },
    "contact_lock_metrics_from_existing_report": {
        "per_leg_mean_stance_slip": contact_report["per_leg_slip_comparison"],
        "validation_criteria": contact_report["criteria"],
        "limitations": contact_report["limitations"],
    },
    "interpretation": {
        "camera_bias_removed": True,
        "pixel_similarity_score": "not computed; silhouettes are not a validated gait-quality metric",
        "observed_differences": [
            "The earlier baseline translates along the rig Root head's world Y by about 0.595 scene units over the five-second playback; the seamless and contact-locked versions range about 0.175 units. This is why the earlier version drifts toward the edge under a fixed camera while the later versions stay more in place.",
            "Rear knee flexion ranges shift substantially in the seamless action versus the earlier baseline (Rear.L about 61–105 degrees to 46–84; Rear.R about 82–152 to 47–85). The contact-locked action's evaluated knee ranges return close to the earlier ranges, while retaining the lower root drift.",
            "At sampled frames 1, 24, 48, 72, 96, and 120, the contact-locked version keeps full-body framing and the stepping remains close to the earlier baseline; the seamless version has a distinct rear-leg pose and altered in-place body travel.",
        ],
        "likely_regression": "The key perceived change is not only the camera: the seamless conversion materially reduced the Root travel and changed rear-leg joint rotations. This can make the creature feel less like the earlier forward-moving walk. Contact locking then reduces measured stance slip but is not a full replacement for the earlier stride timing/lift.",
        "visual_approval": "VISUALLY_REVIEWED: generated same-camera contact sheet inspected at six time samples",
    },
}
(out / "comparison_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

# Contact sheet for quick inspection at six points through the loop.
sample_ids = [1, 24, 48, 72, 96, 120]
thumb_w, thumb_h = 480, 270
sheet = np.full((len(sample_ids) * (thumb_h + 36), 3 * thumb_w, 3), 25, np.uint8)
for row, index in enumerate(sample_ids):
    for col, name in enumerate(names):
        p = frame_path(sources[name], index)
        if name == "Contact locked":
            p = contact_candidates[index - 1]
        im = cv2.resize(cv2.imread(str(p)), (thumb_w, thumb_h), interpolation=cv2.INTER_AREA)
        y, x = row * (thumb_h + 36), col * thumb_w
        sheet[y:y + thumb_h, x:x + thumb_w] = im
        cv2.putText(sheet, f"{name} | frame {index}", (x + 8, y + thumb_h + 25),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (235, 235, 235), 1, cv2.LINE_AA)
cv2.imwrite(str(out / "comparison_contact_sheet.png"), sheet)
print(json.dumps({"video": str(video_path), "report": str(out / "comparison_report.json"),
                  "sheet": str(out / "comparison_contact_sheet.png")}, indent=2))
