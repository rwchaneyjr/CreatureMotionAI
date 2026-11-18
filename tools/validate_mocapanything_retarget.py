"""Physical and motion gate for the MoCapAnything 24-frame Balisk retarget."""
import bpy
import json
import math
import os
from pathlib import Path
from mathutils import Vector

blend = Path(os.environ["CMAI_MOCAP_RETARGET_OUT"])
raw = json.loads(Path(os.environ["CMAI_MOCAP_RETARGET_REPORT"]).read_text(encoding="utf-8"))
out = Path(os.environ["CMAI_MOCAP_FINAL_REPORT"])
bpy.ops.wm.open_mainfile(filepath=str(blend))
scene = bpy.context.scene
rig = bpy.data.objects["CrimsonSpineBehemoth_Rig"]
mesh = bpy.data.objects["CrimsonSpineBehemoth_Mesh"]
source = bpy.data.objects["MoCapAnything_Balisk_24f_BVH"]
ground = raw["original_ground_z"]
legs = sorted(raw["frames"][0]["legs"])
leg_report = {}
for leg in legs:
    frames = [row["legs"][leg] for row in raw["frames"]]
    first, last = frames[0], frames[-1]
    normals = []
    for row in frames:
        h, k, a = (Vector(row[n]) for n in ("hip", "knee", "ankle"))
        v = (k-h).cross(a-k)
        normals.append(v.normalized() if v.length > 1e-6 else None)
    knee_reversals = [i+1 for i,n in enumerate(normals) if n is not None and normals[0] is not None
                      and n.dot(normals[0]) < -0.2]
    slide = []
    for i in range(1, 24):
        if frames[i]["foot_height_over_rest_ground"] <= 0.03 and frames[i-1]["foot_height_over_rest_ground"] <= 0.03:
            p, q = Vector(frames[i]["tip"]), Vector(frames[i-1]["tip"])
            slide.append((Vector((p.x,p.y))-Vector((q.x,q.y))).length)
    leg_report[leg] = {
        "max_tip_displacement_from_rest": max(x["tip_displacement_from_rest"] for x in frames),
        "loop_tip_seam_distance": (Vector(last["tip"])-Vector(first["tip"])).length,
        "max_foot_orientation_change_degrees": max(x["foot_orientation_change_degrees"] for x in frames),
        "minimum_foot_tip_height_over_ground": min(x["foot_height_over_rest_ground"] for x in frames),
        "contact_frame_count": sum(x["foot_height_over_rest_ground"] <= 0.03 for x in frames),
        "max_consecutive_planted_foot_slide": max(slide, default=None),
        "knee_reversal_frames": knee_reversals,
    }

mesh_rows = []
for frame in range(1, 25):
    scene.frame_set(frame)
    ev = mesh.evaluated_get(bpy.context.evaluated_depsgraph_get())
    temp = ev.to_mesh()
    bottom = min((mesh.matrix_world @ v.co).z for v in temp.vertices)
    ev.to_mesh_clear()
    mesh_rows.append({"frame": frame, "mesh_bottom_z": bottom,
                      "new_penetration_from_original_ground": max(0.0, ground-bottom)})

source_local_motion = {}
# Blender does not evaluate a hidden source armature while scrubbing frames.
# Temporarily enable it for diagnostics; this file is never saved by validation.
source.hide_viewport = False
source.hide_set(False)
for leg in legs:
    source_local_motion[leg] = {}
    for number in (1,2,3):
        n = f"{leg}_{number:02d}"
        scene.frame_set(1)
        q1 = source.pose.bones[n].matrix_basis.to_quaternion().copy()
        angles = []
        for frame in range(2, 25):
            scene.frame_set(frame)
            q = source.pose.bones[n].matrix_basis.to_quaternion()
            angles.append(math.degrees(q1.rotation_difference(q).angle))
        source_local_motion[leg][n] = max(angles, default=0.0)
source.hide_set(True)
source.hide_viewport = True

penetrating = [x["frame"] for x in mesh_rows if x["new_penetration_from_original_ground"] > 0.01]
no_lower_leg_motion = [n for data in source_local_motion.values() for n, angle in data.items()
                       if n.endswith(("_02","_03")) and angle < 0.1]
bvh_channel_path = Path(os.environ.get("CMAI_MOCAP_BVH_CHANNEL_REPORT", blend.parent / "bvh_leg_channel_report.json"))
bvh_channels = json.loads(bvh_channel_path.read_text(encoding="utf-8")) if bvh_channel_path.exists() else None
missing_contacts = [leg for leg, data in leg_report.items() if data["contact_frame_count"] == 0]
physical_gate_pass = not penetrating and not no_lower_leg_motion and not missing_contacts
report = {
    "status": "PHYSICAL_GATE_PASS_VISUAL_REVIEW_REQUIRED" if physical_gate_pass else "FAIL_NOT_A_VALID_WALK",
    "installation": "PASS_PREVIOUS_POC",
    "custom_rig_preprocessing": "PASS_PREVIOUS_POC_WITH_BVH_BASIS_CORRECTION_REQUIRED",
    "motion_generation": "HAS_ARTICULATION_PHYSICAL_REVIEW_REQUIRED" if not no_lower_leg_motion else "FAIL_STATIC_LOWER_LEGS",
    "blender_retargeting": "PASS_TECHNICAL_TRANSFER_ON_COPY",
    "original_mesh_deforms": True,
    "eight_leg_movement": "ARTICULATION_PRESENT_PHYSICAL_REVIEW_REQUIRED" if not no_lower_leg_motion else "FAIL_INDEPENDENT_LEG_ARTICULATION",
    "visual_similarity": "NOT_MEASURED_BY_THIS_SCRIPT; inspect synchronized render comparison",
    "original_rig_rest_unchanged": raw["original_bone_rest_matrices_unchanged"],
    "original_actions_preserved": raw["original_actions_preserved"],
    "source_lower_leg_bones_with_less_than_0_1_degree_local_change": no_lower_leg_motion,
    "source_lower_leg_static_count": len(no_lower_leg_motion),
    "source_local_rotation_max_degrees_from_frame_1": source_local_motion,
    "generated_bvh_leg_bones_static_across_all_24_frames": len(bvh_channels["static_leg_bones"]) if bvh_channels else None,
    "generated_bvh_leg_bones_total": len(bvh_channels["leg_channels"]) if bvh_channels else None,
    "bvh_channel_report": str(bvh_channel_path) if bvh_channels else None,
    "leg_metrics": leg_report,
    "mesh_ground_penetration_by_frame": mesh_rows,
    "ground_penetration_frames_over_0_01": penetrating,
    "legs_without_ground_contact": missing_contacts,
    "frames_passing_ground_penetration_check_only": 24-len(penetrating),
    "max_new_mesh_ground_penetration": max(x["new_penetration_from_original_ground"] for x in mesh_rows),
    "loop_created": False,
    "preview_video": None,
    "diagnostic_comparison_video": os.environ.get("CMAI_MOCAP_COMPARISON_VIDEO"),
    "contact_sheet": os.environ.get("CMAI_MOCAP_CONTACT_SHEET"),
    "comparison_alignment": "One fixed first-frame image scale/translation; no pose or per-frame warping",
    "output_blend": str(blend),
    "action": raw["action"],
    "technical_notes": [
        "Official custom-rig BVH offsets are 1/100 of original Blender rig units.",
        "BVH XYZ axes differ from Blender FBX by original=(-BVH_Y,BVH_Z,-BVH_X).",
        "First-frame-relative transfer removes the raw BVH root tilt.",
        "Official output is encoded at 30 FPS while the reference clip is 24 FPS; samples were displayed at 24 FPS for comparison.",
    ],
}
out.write_text(json.dumps(report, indent=2), encoding="utf-8")
print("CMAI_VALIDATION", json.dumps({"status":report["status"],
                                      "ground_penetration_frames":len(penetrating),
                                      "source_lower_leg_static_count":len(no_lower_leg_motion),
                                      "report":str(out)}))
