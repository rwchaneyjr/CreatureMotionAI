"""Create a collision-safe diagnostic copy by holding the last valid pose."""
import argparse
import json
import sys
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.validate_blender_pose_collisions import build_self_collision_bvh, check_frame  # noqa: E402


def snapshot(rig):
    return {b.name: (b.location.copy(), b.rotation_mode, b.rotation_euler.copy(), b.rotation_quaternion.copy(), b.scale.copy()) for b in rig.pose.bones}


def restore(rig, state):
    for name, values in state.items():
        b = rig.pose.bones.get(name)
        if not b:
            continue
        b.location, b.rotation_mode, b.rotation_euler, b.rotation_quaternion, b.scale = values


def key_pose(rig, frame):
    for b in rig.pose.bones:
        b.keyframe_insert("location", frame=frame, group=b.name)
        if b.rotation_mode == "QUATERNION":
            b.keyframe_insert("rotation_quaternion", frame=frame, group=b.name)
        else:
            b.keyframe_insert("rotation_euler", frame=frame, group=b.name)
        b.keyframe_insert("scale", frame=frame, group=b.name)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--source", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--report", required=True)
    p.add_argument("--start", type=int, default=1)
    p.add_argument("--end", type=int, default=None)
    p.add_argument("--ground-z", type=float, default=-0.24)
    p.add_argument("--tolerance", type=float, default=0.05)
    p.add_argument("--proxy-ratio", type=float, default=0.08)
    a = p.parse_args()
    bpy.ops.wm.open_mainfile(filepath=str(Path(a.source).resolve()))
    mesh = next(o for o in bpy.context.scene.objects if o.type == "MESH")
    rig = next(o for o in bpy.context.scene.objects if o.type == "ARMATURE")
    end = a.end or bpy.context.scene.frame_end
    last_valid = None
    rows = []
    for frame in range(a.start, end + 1):
        bpy.context.scene.frame_set(frame)
        depsgraph = bpy.context.evaluated_depsgraph_get()
        evaluated, data, tree, tris = build_self_collision_bvh(mesh, depsgraph, a.proxy_ratio)
        row = check_frame(mesh, rig, a.ground_z, a.tolerance, tree, tris)
        evaluated.to_mesh_clear()
        if row["self_collision_pairs"]:
            exact_eval = mesh.evaluated_get(depsgraph)
            exact_data = exact_eval.to_mesh()
            exact_data.calc_loop_triangles()
            verts = [mesh.matrix_world @ v.co for v in exact_data.vertices]
            exact_tris = [tuple(t.vertices) for t in exact_data.loop_triangles]
            from mathutils.bvhtree import BVHTree
            exact_tree = BVHTree.FromPolygons(verts, exact_tris, all_triangles=True)
            row = check_frame(mesh, rig, a.ground_z, a.tolerance, exact_tree, exact_tris)
            exact_eval.to_mesh_clear()
        row["frame"] = frame
        if row["accepted"]:
            last_valid = snapshot(rig)
            row["action"] = "kept"
        elif last_valid is not None:
            restore(rig, last_valid)
            key_pose(rig, frame)
            row["action"] = "held_previous_valid_pose"
        else:
            row["action"] = "held_original_first_pose"
        rows.append(row)
    report = {"source": str(Path(a.source).resolve()), "output": str(Path(a.output).resolve()), "frames": rows, "kept": sum(r["action"] == "kept" for r in rows), "held": sum(r["action"] == "held_previous_valid_pose" for r in rows)}
    Path(a.report).parent.mkdir(parents=True, exist_ok=True)
    Path(a.report).write_text(json.dumps(report, indent=2), encoding="utf-8")
    bpy.ops.wm.save_as_mainfile(filepath=str(Path(a.output).resolve()))
    print(json.dumps({"output": str(a.output), "kept": report["kept"], "held": report["held"]}))


if __name__ == "__main__":
    main()
