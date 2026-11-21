import bpy, math, json
from pathlib import Path
from mathutils import Quaternion, Matrix
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[1] / "data/generated/hydra_two_view_500_pose_pilot"
SOURCE = ROOT / "hydra_two_view_march_candidate_5s.blend"
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
scene = bpy.context.scene
arm = bpy.data.objects["SevenHeadedHydra_Rig"]
mesh = bpy.data.objects["SevenHeadedHydra_Mesh"]
action = bpy.data.actions["CMAI_Hydra_TwoViewMarch_5s"]
ad = arm.animation_data or arm.animation_data_create()
ad.action = action
if action.slots and hasattr(ad, "action_slot"):
    ad.action_slot = action.slots[0]

collider = mesh.copy()
collider.data = mesh.data.copy()
collider.name = "CMAI_TEMP_GaitProbeCollider"
scene.collection.objects.link(collider)
for mod in list(collider.modifiers):
    collider.modifiers.remove(mod)
dec = collider.modifiers.new("CMAI_TEMP_Decimate", "DECIMATE")
dec.ratio = 0.004
bpy.context.view_layer.objects.active = collider
collider.select_set(True)
bpy.ops.object.modifier_apply(modifier=dec.name)
collider.select_set(False)
skin = collider.modifiers.new("CMAI_TEMP_Armature", "ARMATURE")
skin.object = arm

def update():
    bpy.context.view_layer.update()

def snapshot():
    return {bone.name: bone.matrix_basis.copy() for bone in arm.pose.bones}

def apply(pose):
    for bone in arm.pose.bones:
        bone.matrix_basis = pose[bone.name].copy()
    update()

def rotate(pose, name, axis, degrees):
    loc, quat, scale = pose[name].decompose()
    quat = quat @ Quaternion(axis, math.radians(degrees))
    pose[name] = Matrix.LocRotScale(loc, quat, scale)

def surface_pairs():
    evaluated = collider.evaluated_get(bpy.context.evaluated_depsgraph_get())
    evaluated_mesh = evaluated.to_mesh()
    world = evaluated.matrix_world
    vertices = [world @ vertex.co for vertex in evaluated_mesh.vertices]
    polygons = [tuple(poly.vertices) for poly in evaluated_mesh.polygons]
    tree = BVHTree.FromPolygons(vertices, polygons, all_triangles=True)
    overlap = tree.overlap(tree)
    pairs = set()
    for a, b in overlap:
        if a == b:
            continue
        x, y = (a, b) if a < b else (b, a)
        if set(polygons[x]).isdisjoint(polygons[y]):
            pairs.add((x, y))
    evaluated.to_mesh_clear()
    return pairs

def bend_vector(names):
    points = [arm.matrix_world @ arm.pose.bones[name].head for name in names]
    points.append(arm.matrix_world @ arm.pose.bones[names[-1]].tail)
    return (points[1] - points[0]).cross(points[2] - points[1])

trials = [
    {"name":"leg2_lift3_knee1", "stride":2, "lift":3, "knee":1, "shoulder":0, "elbow":0},
    {"name":"leg3_lift4_knee2", "stride":3, "lift":4, "knee":2, "shoulder":0, "elbow":0},
    {"name":"leg4_lift5_knee2", "stride":4, "lift":5, "knee":2, "shoulder":0, "elbow":0},
    {"name":"leg3_lift4_knee2_arm2", "stride":3, "lift":4, "knee":2, "shoulder":-2, "elbow":1},
    {"name":"leg6_lift8_knee4", "stride":6, "lift":8, "knee":4, "shoulder":0, "elbow":0},
    {"name":"leg8_lift10_knee5", "stride":8, "lift":10, "knee":5, "shoulder":0, "elbow":0},
    {"name":"leg10_lift12_knee6", "stride":10, "lift":12, "knee":6, "shoulder":0, "elbow":0},
    {"name":"leg6_lift8_knee4_arm3", "stride":6, "lift":8, "knee":4, "shoulder":-3, "elbow":2},
    {"name":"leg6_lift8_knee4_arm6", "stride":6, "lift":8, "knee":4, "shoulder":-6, "elbow":3},
]
frames = list(range(1, 121, 12)) + [120]
base = {}
base_pairs = {}
base_bends = {}
for frame in frames:
    scene.frame_set(frame)
    update()
    base[frame] = snapshot()
    base_pairs[frame] = surface_pairs()
    base_bends[frame] = {side: bend_vector([f"Leg.{side}_{i:02d}" for i in (1,2,3)]) for side in ("L","R")}

results = []
for trial in trials:
    added_max = 0
    bend_ok = True
    for frame in frames:
        phase = 2.0 * math.pi * (frame - 1) / 60.0
        pose = {name: matrix.copy() for name, matrix in base[frame].items()}
        for side in ("L", "R"):
            ph = phase + (math.pi if side == "R" else 0.0)
            stride = math.sin(ph)
            swing = max(0.0, math.sin(ph))
            rotate(pose, f"Leg.{side}_01", (0,0,1), trial["stride"] * stride)
            rotate(pose, f"Leg.{side}_01", (1,0,0), trial["lift"] * swing)
            rotate(pose, f"Leg.{side}_02", (1,0,0), -trial["knee"] * swing)
            if trial["shoulder"]:
                rotate(pose, f"Arm.{side}_01", (1,0,0), trial["shoulder"])
                rotate(pose, f"Arm.{side}_02", (1,0,0), trial["elbow"])
        apply(pose)
        added = len(surface_pairs() - base_pairs[frame])
        added_max = max(added_max, added)
        for side in ("L", "R"):
            current = bend_vector([f"Leg.{side}_{i:02d}" for i in (1,2,3)])
            baseline = base_bends[frame][side]
            if current.length > 1e-8 and baseline.length > 1e-8 and current.dot(baseline) < 0:
                bend_ok = False
    results.append({**trial, "sampled_frames":len(frames), "max_added_surface_intersections":added_max, "knee_direction_preserved":bend_ok, "passes_probe":added_max == 0 and bend_ok})
    print("PROBE", json.dumps(results[-1]), flush=True)

report = ROOT / "hydra_reference_gait_probe.json"
report.write_text(json.dumps({"source_blend":str(SOURCE),"base_action":action.name,"sampled_frames":frames,"method":"decimated evaluated skinned mesh BVH self-overlap; added non-adjacent triangle-pair count relative to same base frame","results":results}, indent=2))
bpy.data.objects.remove(collider, do_unlink=True)
print("REPORT", report, flush=True)
