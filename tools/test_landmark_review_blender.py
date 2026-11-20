"""Headless Blender integration check for the single-leg landmark reviewer."""
import json
import sys
from pathlib import Path
import bpy

ROOT = Path(__file__).resolve().parents[1]
REVIEW = ROOT / "data/generated/reference_leg_identity_review/460facd3db_8fd7b03ec4_leftpanel_v2"
BLEND_OUT = REVIEW / "landmark_review_ui_test.blend"
REPORT = REVIEW / "blender_ui_test_report.json"

bpy.ops.wm.open_mainfile(filepath=str(ROOT / "data/generated/original_static_standing.blend"))
old_package = sys.modules.get("creature_motion_ai")
if old_package and hasattr(old_package, "unregister"):
    try:
        old_package.unregister()
    except Exception:
        pass
for module_name in list(sys.modules):
    if module_name == "creature_motion_ai" or module_name.startswith("creature_motion_ai."):
        del sys.modules[module_name]
sys.path.insert(0, str(ROOT))
import creature_motion_ai
assert Path(creature_motion_ai.__file__).resolve().is_relative_to(ROOT.resolve()), creature_motion_ai.__file__
from creature_motion_ai.landmark_review import _find_leg_chain

creature_motion_ai.register()
scene = bpy.context.scene
review_path = REVIEW / "landmark_review.json"
data = json.loads(review_path.read_text(encoding="utf-8"))
scene.cmai_landmark_review_data = str(review_path)
scene.cmai_landmark_review_samples = str(REVIEW)
scene.cmai_landmark_review_frame = 15
scene.cmai_landmark_review_camera = "camera_A"
scene.cmai_landmark_review_landmark = "Leg_Reference_hip"
scene.cmai_reference_leg_identity = "UNVERIFIED"
scene.cmai_show_landmark_predictions = False

arm, names = _find_leg_chain("Rear.L")
parents = [arm.data.bones[n].parent.name if arm.data.bones[n].parent else None for n in names]
assert len(arm.data.bones) == 38, len(arm.data.bones)
assert parents[1:] == names[:2], parents
assert scene.cmai_show_landmark_predictions is False
assert bpy.ops.cmai.review_set_visibility.get_rna_type()
assert bpy.ops.cmai.confirm_reference_leg_identity.get_rna_type()
assert bpy.ops.cmai.review_all_landmarks.get_rna_type()
assert data["review_image_transform"] == "crop_left_panel_x0_640_no_scale"
assert data["identity_verified"] is False
frame = next(r for r in data["frames"] if r["frame"] == 15)
points = frame["camera_A"]["landmarks"]
assert len(points) == 4 and all(p["state"] == "prediction_only" for p in points.values())

# Configure the saved test copy to open directly into the side reference Image Editor.
areas = [a for screen in bpy.data.screens for a in screen.areas]
image_area = next((a for a in areas if a.type == "IMAGE_EDITOR"), None)
if image_area is None:
    image_area = next(a for a in areas if a.type == "VIEW_3D")
    image_area.type = "IMAGE_EDITOR"
image_area.spaces.active.image = bpy.data.images.load(str(REVIEW / "frame_000015_camera_A.png"), check_existing=True)
image_area.spaces.active.show_region_ui = True
scene.cmai_identity_approval_file = ""

BLEND_OUT.parent.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_OUT))
REPORT.write_text(json.dumps({
    "status": "PASS",
    "original_blend": str(ROOT / "data/generated/original_static_standing.blend"),
    "test_blend_copy": str(BLEND_OUT),
    "armature": arm.name,
    "bone_count": len(arm.data.bones),
    "rear_left_chain": names,
    "parent_chain": parents,
    "review_image_transform": data["review_image_transform"],
    "predictions_visible_by_default": scene.cmai_show_landmark_predictions,
    "initially_approved": data["identity_verified"],
    "status_controls": ["VISIBLE", "OCCLUDED", "UNVERIFIED"],
    "animation_generated": False,
}, indent=2), encoding="utf-8")
print(REPORT.read_text(encoding="utf-8"))
