"""Build a separate, reference-guided Hydra loop from the current validated candidate.

The source rig and all source Actions remain untouched. The gait is additive and
conservative because larger tested swings introduced new mesh intersections.
"""
import bpy, json, math, time
from pathlib import Path
from mathutils import Quaternion, Matrix
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[1] / "data/generated/hydra_two_view_500_pose_pilot"
SOURCE = ROOT / "hydra_two_view_march_candidate_5s.blend"
OUTPUT = ROOT / "hydra_reference_guided_walk_5s_v3.blend"
REPORT = ROOT / "hydra_reference_guided_walk_5s_v3_report.json"
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
scene = bpy.context.scene
arm = bpy.data.objects["SevenHeadedHydra_Rig"]
mesh = bpy.data.objects["SevenHeadedHydra_Mesh"]
base_action = bpy.data.actions["CMAI_Hydra_TwoViewMarch_5s"]
ad = arm.animation_data or arm.animation_data_create()
ad.action = base_action
if base_action.slots and hasattr(ad, "action_slot"):
    ad.action_slot = base_action.slots[0]

chains = {side: [f"Leg.{side}_{i:02d}" for i in (1,2,3)] for side in ("L","R")}
for side_names in chains.values():
    if any(name not in arm.pose.bones for name in side_names):
        raise RuntimeError(f"Missing leg chain: {side_names}")

ground = bpy.data.objects.get("CMAI_Hydra_Preview_Ground")
ground_z = min((ground.matrix_world @ vert.co).z for vert in ground.data.vertices) if ground and ground.type == "MESH" else -0.59
collider = mesh.copy()
collider.data = mesh.data.copy()
collider.name = "CMAI_TEMP_ReferenceLoopCollider"
scene.collection.objects.link(collider)
for modifier in list(collider.modifiers):
    collider.modifiers.remove(modifier)
decimate = collider.modifiers.new("CMAI_TEMP_Decimate", "DECIMATE")
decimate.ratio = 0.004
bpy.context.view_layer.objects.active = collider
collider.select_set(True)
bpy.ops.object.modifier_apply(modifier=decimate.name)
collider.select_set(False)
armature_mod = collider.modifiers.new("CMAI_TEMP_Skin", "ARMATURE")
armature_mod.object = arm

def update():
    bpy.context.view_layer.update()

def snapshot():
    return {bone.name: bone.matrix_basis.copy() for bone in arm.pose.bones}

def apply(pose):
    for bone in arm.pose.bones:
        bone.matrix_basis = pose[bone.name].copy()
    update()

def rotate(pose, name, axis, degrees):
    if abs(degrees) < 1e-8:
        return
    location, rotation, scale = pose[name].decompose()
    rotation = rotation @ Quaternion(axis, math.radians(degrees))
    pose[name] = Matrix.LocRotScale(location, rotation, scale)

def mesh_state():
    evaluated = collider.evaluated_get(bpy.context.evaluated_depsgraph_get())
    evaluated_mesh = evaluated.to_mesh()
    world = evaluated.matrix_world
    vertices = [world @ vertex.co for vertex in evaluated_mesh.vertices]
    polygons = [tuple(poly.vertices) for poly in evaluated_mesh.polygons]
    tree = BVHTree.FromPolygons(vertices, polygons, all_triangles=True)
    overlaps = tree.overlap(tree)
    pairs = set()
    for a, b in overlaps:
        if a == b:
            continue
        x, y = (a, b) if a < b else (b, a)
        if set(polygons[x]).isdisjoint(polygons[y]):
            pairs.add((x, y))
    min_z = min(vertex.z for vertex in vertices)
    evaluated.to_mesh_clear()
    return pairs, min_z

def bend_vector(names):
    points = [arm.matrix_world @ arm.pose.bones[name].head for name in names]
    points.append(arm.matrix_world @ arm.pose.bones[names[-1]].tail)
    return (points[1]-points[0]).cross(points[2]-points[1])

def bone_length_ratios():
    ratios = []
    for side_names in chains.values():
        for name in side_names:
            current = (arm.pose.bones[name].tail - arm.pose.bones[name].head).length
            rest = arm.data.bones[name].length
            ratios.append(current/rest if rest else 1.0)
    return ratios

# Two complete alternating gait periods in 120 frames. Values are the largest
# tested pose that had zero added mesh intersections on all 11 probe samples.
PARAMS = {"cycle_frames":60, "stride_deg":2.0, "swing_lift_deg":3.0,
          "knee_flex_deg":1.0, "shoulder_bend_deg":0.0,
          "elbow_bend_deg":0.0, "motion_scale":1.0}
frames = list(range(1, 122))  # frame 121 repeats frame 1 for a clean loop boundary
baseline = {}
baseline_pairs = {}
baseline_z = {}
baseline_bends = {}
for frame in range(1, 121):
    scene.frame_set(frame)
    update()
    baseline[frame] = snapshot()
    baseline_pairs[frame], baseline_z[frame] = mesh_state()
    baseline_bends[frame] = {side:bend_vector(names) for side,names in chains.items()}
baseline[121] = {name:matrix.copy() for name,matrix in baseline[1].items()}
baseline_pairs[121] = set(baseline_pairs[1])
baseline_z[121] = baseline_z[1]
baseline_bends[121] = {side:value.copy() for side,value in baseline_bends[1].items()}

poses = {}
rows = []
for frame in frames:
    phase = 2.0 * math.pi * (frame - 1) / PARAMS["cycle_frames"]
    pose = {name:matrix.copy() for name,matrix in baseline[frame].items()}
    leg_phase = {}
    for side in ("L","R"):
        ph = phase + (math.pi if side == "R" else 0.0)
        stride = math.sin(ph)
        swing = max(0.0, math.sin(ph))
        rotate(pose, f"Leg.{side}_01", (0,0,1), PARAMS["stride_deg"]*stride)
        rotate(pose, f"Leg.{side}_01", (1,0,0), PARAMS["swing_lift_deg"]*swing)
        rotate(pose, f"Leg.{side}_02", (1,0,0), -PARAMS["knee_flex_deg"]*swing)
        # Small arm adjustment only; stronger arm bending was collision-rejected.
        rotate(pose, f"Arm.{side}_01", (1,0,0), PARAMS["shoulder_bend_deg"])
        rotate(pose, f"Arm.{side}_02", (1,0,0), PARAMS["elbow_bend_deg"])
        leg_phase[side] = {"stride_deg":PARAMS["stride_deg"]*stride,
                           "swing_lift_deg":PARAMS["swing_lift_deg"]*swing,
                           "knee_flex_deg":-PARAMS["knee_flex_deg"]*swing}
    apply(pose)
    pairs, min_z = mesh_state()
    bend_ok = True
    for side,names in chains.items():
        current = bend_vector(names)
        base = baseline_bends[frame][side]
        if current.length > 1e-8 and base.length > 1e-8 and current.dot(base) < -1e-8:
            bend_ok = False
    ratios = bone_length_ratios()
    penetration = max(0.0, ground_z-min_z)
    baseline_penetration = max(0.0, ground_z-baseline_z[frame])
    added_pairs = len(pairs-baseline_pairs[frame])
    valid = (added_pairs == 0 and bend_ok and penetration <= baseline_penetration+0.01
             and min(ratios) >= 0.985 and max(ratios) <= 1.015)
    poses[frame] = snapshot()
    rows.append({"frame":frame,"new_surface_intersection_pairs":added_pairs,
                 "knee_direction_preserved":bend_ok,"ground_penetration_m":penetration,
                 "baseline_ground_penetration_m":baseline_penetration,
                 "bone_length_ratio_min":min(ratios),"bone_length_ratio_max":max(ratios),
                 "limb_offsets":leg_phase,"passes_safety":valid})
    if frame % 24 == 0:
        print("VALIDATE", frame, "PASS" if valid else "FAIL", "new_pairs", added_pairs, flush=True)

failed = [row for row in rows if not row["passes_safety"]]
if failed:
    bpy.data.objects.remove(collider, do_unlink=True)
    REPORT.write_text(json.dumps({"status":"REJECTED_FULL_FRAME_SAFETY",
        "source_blend":str(SOURCE),"failed_frames":[r["frame"] for r in failed],
        "frame_results":rows,"probe_report":str(ROOT/"hydra_reference_gait_probe.json")}, indent=2))
    raise SystemExit("Candidate rejected; no Blender file saved")

new_action = bpy.data.actions.new("CMAI_Hydra_ReferenceGuided_Walk_5s_v2")
ad.action = new_action
if new_action.slots and hasattr(ad, "action_slot"):
    ad.action_slot = new_action.slots[0]
for frame in frames:
    scene.frame_set(frame)
    apply(poses[frame])
    for bone in arm.pose.bones:
        bone.keyframe_insert(data_path="location", frame=frame, group=bone.name)
        if bone.rotation_mode == "QUATERNION":
            bone.keyframe_insert(data_path="rotation_quaternion", frame=frame, group=bone.name)
        else:
            bone.keyframe_insert(data_path="rotation_euler", frame=frame, group=bone.name)
        bone.keyframe_insert(data_path="scale", frame=frame, group=bone.name)
scene.frame_start, scene.frame_end, scene.render.fps = 1, 120, 24
scene.frame_set(1)
bpy.data.objects.remove(collider, do_unlink=True)
bpy.ops.wm.save_as_mainfile(filepath=str(OUTPUT))
report = {"status":"FULL_FRAME_SAFETY_PASS_VISUAL_MATCH_REQUIRES_REVIEW",
    "source_blend":str(SOURCE),"output_blend":str(OUTPUT),"base_action":base_action.name,
    "new_action":new_action.name,"rig_bones":len(arm.data.bones),"tested_frames":120,
    "passed_frames":len(rows)-len(failed),"fps":24,"duration_seconds":5,
    "loop_boundary_keyed_at_frame_121":True,
    "method":"Additive, reference-guided in-place gait on the current action; not mocap and not per-pixel fitted.",
    "parameters":PARAMS,"max_added_surface_intersection_pairs":max(r["new_surface_intersection_pairs"] for r in rows),
    "max_ground_penetration_m":max(r["ground_penetration_m"] for r in rows),
    "knee_direction_preserved_all_frames":all(r["knee_direction_preserved"] for r in rows),
    "bone_length_ratio_range":[min(r["bone_length_ratio_min"] for r in rows),max(r["bone_length_ratio_max"] for r in rows)],
    "frame_results":rows,
    "limitations":["Reference clips are independently sampled and not verified synchronized.",
       "Mesh collision check uses the decimated evaluated skinned surface and compares added intersections to the source pose.",
       "Foot contacts are not locked in world space; this loop is an in-place, reference-guided gait, not exact video reproduction.",
       "The current armature has two leg chains and two arm chains; it is not a seven-leg rig."]}
REPORT.write_text(json.dumps(report,indent=2))
print("SAVED", json.dumps({"blend":str(OUTPUT),"action":new_action.name,"report":str(REPORT),"passed_frames":len(rows)-len(failed)},), flush=True)
