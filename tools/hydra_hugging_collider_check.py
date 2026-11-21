"""Compare a small Hydra pose candidate against the exact skinned mesh surface.

This is an isolated diagnostic: it loads a copy, never saves over the source,
and tests limb-surface intersections against the remaining evaluated mesh.
"""
import bpy
import json
import math
import sys
import time
from pathlib import Path
from mathutils import Quaternion, Matrix
from mathutils.bvhtree import BVHTree

ROOT = Path(r"C:\Users\rober\CreatureMotionAI\data\generated\hydra_two_view_500_pose_pilot")
SRC = ROOT / "hydra_two_view_march_candidate_5s.blend"
OUT = ROOT / "hydra_hugging_mesh_collider_report.json"
bpy.ops.wm.open_mainfile(filepath=str(SRC))
scene = bpy.context.scene
arm = bpy.data.objects["SevenHeadedHydra_Rig"]
mesh = bpy.data.objects["SevenHeadedHydra_Mesh"]
action = bpy.data.actions["CMAI_Hydra_TwoViewMarch_5s"]
arm.animation_data.action = action
if action.slots and hasattr(arm.animation_data, "action_slot"):
    arm.animation_data.action_slot = action.slots[0]

chains = {
    "Arm.L": [f"Arm.L_{i:02d}" for i in (1, 2, 3)],
    "Arm.R": [f"Arm.R_{i:02d}" for i in (1, 2, 3)],
    "Leg.L": [f"Leg.L_{i:02d}" for i in (1, 2, 3)],
    "Leg.R": [f"Leg.R_{i:02d}" for i in (1, 2, 3)],
}
limb_groups = {key: set(names) for key, names in chains.items()}
group_names = {g.index: g.name for g in mesh.vertex_groups}
group_to_limb = {name: limb for limb, names in limb_groups.items() for name in names}

def add_axis(pose, bone_name, axis, degrees):
    loc, rot, scale = pose[bone_name].decompose()
    pose[bone_name] = Matrix.LocRotScale(
        loc, rot @ Quaternion(axis, math.radians(degrees)), scale
    )

def update_pose(frame, bent=False):
    scene.frame_set(frame)
    bpy.context.view_layer.update()
    if not bent:
        return
    # Conservative folded-arm adjustment, additive to the existing action.
    for side in ("L", "R"):
        p1 = arm.pose.bones[f"Arm.{side}_01"]
        p2 = arm.pose.bones[f"Arm.{side}_02"]
        p1.matrix_basis = p1.matrix_basis @ Matrix.Rotation(math.radians(-9.0), 4, "X")
        p2.matrix_basis = p2.matrix_basis @ Matrix.Rotation(math.radians(8.0), 4, "Z")
    bpy.context.view_layer.update()

def evaluated_regions():
    deps = bpy.context.evaluated_depsgraph_get()
    ev = mesh.evaluated_get(deps)
    me = ev.to_mesh(preserve_all_data_layers=True, depsgraph=deps)
    me.calc_loop_triangles()
    world = ev.matrix_world
    coords = [world @ v.co for v in me.vertices]
    # Dominant deform group assignment per triangle; region meshes retain exact
    # evaluated vertex positions and only partition triangles for pair queries.
    tri_ids = [tuple(t.vertices) for t in me.loop_triangles]
    regions = {name: [] for name in (*chains.keys(), "core")}
    for tri_idx, tri in enumerate(tri_ids):
        scores = {limb: 0.0 for limb in chains}
        for vi in tri:
            for g in me.vertices[vi].groups:
                gname = group_names.get(g.group)
                limb = group_to_limb.get(gname)
                if limb:
                    scores[limb] += g.weight / 3.0
        limb, score = max(scores.items(), key=lambda kv: kv[1])
        regions[limb if score >= 0.34 else "core"].append((tri_idx, tri))
    me.calc_loop_triangles()
    ev.to_mesh_clear()
    return coords, tri_ids, regions

def region_tree(coords, tris):
    if not tris:
        return None
    verts_used = sorted({vi for _, tri in tris for vi in tri})
    remap = {old: new for new, old in enumerate(verts_used)}
    local_coords = [coords[i] for i in verts_used]
    local_tris = [tuple(remap[i] for i in tri) for _, tri in tris]
    tree = BVHTree.FromPolygons(local_coords, local_tris, all_triangles=True)
    return tree, local_tris, tris

def intersections(coords, tri_ids, regions):
    core = region_tree(coords, regions["core"])
    found = {}
    for limb in chains:
        side = region_tree(coords, regions[limb])
        count = 0
        if core and side:
            tree_a, local_a, source_a = side
            tree_b, local_b, source_b = core
            for ia, ib in tree_a.overlap(tree_b):
                # Surface continuity across shared original vertices is not a
                # self-collision; non-adjacent intersecting surfaces are.
                ta = set(source_a[ia][1]); tb = set(source_b[ib][1])
                if ta.isdisjoint(tb):
                    count += 1
        found[limb] = count
    return found

def main():
    # Lightweight representative check: baseline pose and one stride-phase pose.
    samples = [1, 12]
    result = {
        "status": "EXACT_EVALUATED_MESH_SURFACE_TEST",
        "source_blend": str(SRC),
        "mesh_object": mesh.name,
        "vertex_count_evaluated": None,
        "triangle_count_evaluated": None,
        "triangle_regions_by_dominant_skin_weight": {},
        "frames": [],
        "method": "At each sampled frame, BVHs are built from the full-resolution evaluated, armature-deformed mesh triangles. Each limb region is tested against the remaining core surface. Triangle pairs sharing source mesh vertices are excluded as normal topology adjacency.",
        "limits": "This is a surface intersection check; it reports intersections between skin-weight regions and does not treat close proximity without surface crossing as collision.",
    }
    for frame in samples:
        per_frame = {"frame": frame}
        for label, bent in (("baseline", False), ("bent_arm_candidate", True)):
            update_pose(frame, bent)
            t0 = time.time()
            coords, tris, regions = evaluated_regions()
            counts = intersections(coords, tris, regions)
            per_frame[label] = {
                "vertex_count": len(coords),
                "triangle_count": len(tris),
                "region_triangles": {k: len(v) for k, v in regions.items()},
                "limb_vs_core_intersections": counts,
                "total_intersections": sum(counts.values()),
                "elapsed_seconds": round(time.time() - t0, 2),
            }
            if result["vertex_count_evaluated"] is None:
                result["vertex_count_evaluated"] = len(coords)
                result["triangle_count_evaluated"] = len(tris)
                result["triangle_regions_by_dominant_skin_weight"] = {k: len(v) for k, v in regions.items()}
        per_frame["delta_intersections_vs_baseline"] = {
            limb: per_frame["bent_arm_candidate"]["limb_vs_core_intersections"][limb]
            - per_frame["baseline"]["limb_vs_core_intersections"][limb]
            for limb in chains
        }
        result["frames"].append(per_frame)
        print("HUG_COLLIDER_FRAME", json.dumps(per_frame), flush=True)
    deltas = [v for fr in result["frames"] for v in fr["delta_intersections_vs_baseline"].values()]
    result["summary"] = {
        "sampled_frames": len(samples),
        "positive_delta_frame_limb_pairs": sum(v > 0 for v in deltas),
        "negative_delta_frame_limb_pairs": sum(v < 0 for v in deltas),
        "zero_delta_frame_limb_pairs": sum(v == 0 for v in deltas),
        "max_added_intersections_in_one_region": max(deltas, default=0),
        "candidate_safety_result": "NO_NEW_INTERSECTIONS_IN_SAMPLED_FRAMES" if all(v <= 0 for v in deltas) else "NEW_INTERSECTIONS_DETECTED",
    }
    OUT.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print("HUG_COLLIDER_REPORT", str(OUT), json.dumps(result["summary"]), flush=True)

main()
