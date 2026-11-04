"""Non-destructive Blender pose safety checks using evaluated mesh raycasts.

This is a validation gate, not an animator. It checks the current evaluated
pose and can be called for every frame before a pose is accepted.
"""

import argparse
import json
import sys
from pathlib import Path

import bpy
from mathutils.bvhtree import BVHTree
from mathutils import Vector


LEG_ROOTS = (
    "Leg_Front.L", "Leg_Front.R", "Leg_MidFront.L", "Leg_MidFront.R",
    "Leg_MidRear.L", "Leg_MidRear.R", "Leg_Rear.L", "Leg_Rear.R",
)


def find_mesh():
    return next((o for o in bpy.context.scene.objects if o.type == "MESH"), None)


def bone_point(armature, name, tail=False):
    bone = armature.pose.bones.get(name)
    if not bone:
        return None
    return armature.matrix_world @ (bone.tail if tail else bone.head)


def build_self_collision_bvh(mesh, depsgraph, proxy_ratio=0.08):
    evaluated = mesh.evaluated_get(depsgraph)
    data = evaluated.to_mesh()
    proxy = bpy.data.objects.new("CMAI_TemporaryCollisionProxy", data.copy())
    bpy.context.scene.collection.objects.link(proxy)
    modifier = proxy.modifiers.new("CMAI_CollisionDecimate", "DECIMATE")
    modifier.ratio = proxy_ratio
    depsgraph.update()
    proxy_eval = proxy.evaluated_get(depsgraph)
    proxy_data = proxy_eval.to_mesh()
    vertices = [proxy.matrix_world @ v.co for v in proxy_data.vertices]
    proxy_data.calc_loop_triangles()
    triangles = [tuple(tri.vertices) for tri in proxy_data.loop_triangles]
    tree = BVHTree.FromPolygons(vertices, triangles, all_triangles=True)
    bpy.data.objects.remove(proxy, do_unlink=True)
    return evaluated, proxy_eval, tree, triangles


def check_frame(mesh, armature, ground_z, tolerance, collision_tree, triangles):
    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated = mesh.evaluated_get(depsgraph)
    failures = []
    warnings = []
    contacts = 0
    self_hits = []
    for a, b in collision_tree.overlap(collision_tree):
        if a >= b or set(triangles[a]).intersection(triangles[b]):
            continue
        self_hits.append({"triangle_a": a, "triangle_b": b})
    if self_hits:
        failures.append({"reason": "mesh_self_intersection", "pair_count": len(self_hits), "pairs": self_hits[:50]})
    for root in LEG_ROOTS:
        foot = bone_point(armature, root + "_03", tail=True)
        knee = bone_point(armature, root + "_02", tail=True)
        hip = bone_point(armature, root + "_01", tail=False)
        if not foot or not knee or not hip:
            failures.append({"leg": root, "reason": "missing_bone_chain"})
            continue
        if foot.z < ground_z - tolerance:
            failures.append({"leg": root, "reason": "foot_below_ground", "z": foot.z})
        else:
            contacts += int(abs(foot.z - ground_z) <= tolerance)
        # A collapsed chain is a strong indicator of a bad IK target.
        if (foot - hip).length < tolerance * 2.0:
            failures.append({"leg": root, "reason": "collapsed_leg"})
        # Raycast from just above the foot downward.  A hit immediately above
        # the foot means the foot is inside the evaluated creature mesh.
        origin = foot + Vector((0.0, 0.0, tolerance))
        direction = Vector((0.0, 0.0, -1.0))
        hit, location, normal, index = evaluated.ray_cast(origin, direction, distance=tolerance * 2.0)
        if hit and (location - foot).length < tolerance:
            # The source asset is a single combined skinned mesh, so this
            # ray can hit the foot/toe geometry itself.  Without a separate
            # body collider that is not proof of self-intersection.
            warnings.append({"leg": root, "reason": "ray_hit_combined_mesh_needs_body_proxy"})
    return {"contacts": contacts, "self_collision_pairs": len(self_hits), "failures": failures, "warnings": warnings, "accepted": not failures and contacts >= 2}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--start", type=int, default=1)
    parser.add_argument("--end", type=int, default=None)
    parser.add_argument("--ground-z", type=float, default=None, help="Ground height; omit to derive from the first pose")
    parser.add_argument("--tolerance", type=float, default=0.03)
    parser.add_argument("--proxy-ratio", type=float, default=0.08)
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    args = parser.parse_args(argv)
    mesh = find_mesh()
    armature = next((o for o in bpy.context.scene.objects if o.type == "ARMATURE"), None)
    if not mesh or not armature:
        raise RuntimeError("Scene must contain a mesh and armature")
    ground_z = args.ground_z
    if ground_z is None:
        ground_z = bpy.context.scene.get("CMAI_GROUND_Z")
    if ground_z is None:
        bpy.context.scene.frame_set(args.start)
        feet = [bone_point(armature, root + "_03", tail=True) for root in LEG_ROOTS]
        feet = [p.z for p in feet if p is not None]
        ground_z = min(feet) if feet else 0.0
    end = args.end or bpy.context.scene.frame_end
    rows = []
    for frame in range(args.start, end + 1):
        bpy.context.scene.frame_set(frame)
        depsgraph = bpy.context.evaluated_depsgraph_get()
        evaluated, mesh_data, collision_tree, triangles = build_self_collision_bvh(mesh, depsgraph, args.proxy_ratio)
        row = check_frame(mesh, armature, ground_z, args.tolerance, collision_tree, triangles)
        evaluated.to_mesh_clear()
        if row["self_collision_pairs"]:
            # Decimation can create artificial triangle crossings. Confirm
            # only flagged frames against the full evaluated mesh.
            exact_eval = mesh.evaluated_get(depsgraph)
            exact_data = exact_eval.to_mesh()
            exact_data.calc_loop_triangles()
            exact_vertices = [mesh.matrix_world @ v.co for v in exact_data.vertices]
            exact_triangles = [tuple(t.vertices) for t in exact_data.loop_triangles]
            exact_tree = BVHTree.FromPolygons(exact_vertices, exact_triangles, all_triangles=True)
            exact_row = check_frame(mesh, armature, ground_z, args.tolerance, exact_tree, exact_triangles)
            exact_eval.to_mesh_clear()
            exact_row["proxy_self_collision_pairs"] = row["self_collision_pairs"]
            exact_row["self_collision_confirmed"] = bool(exact_row["self_collision_pairs"])
            row = exact_row
        row["frame"] = frame
        rows.append(row)
    result = {"blend": bpy.data.filepath, "frames": rows, "accepted_frames": sum(int(r["accepted"]) for r in rows), "total_frames": len(rows), "note": "Safety validation only; accepted frames still require visual comparison."}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(args.output), "accepted_frames": result["accepted_frames"], "total_frames": result["total_frames"]}))


if __name__ == "__main__":
    main()
