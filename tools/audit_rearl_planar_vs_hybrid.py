"""Read-only comparison of the preserved Rear.L planar and hybrid test files."""
import argparse
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector


CHAIN = [f"Leg_Rear.L_{index:02}" for index in (1, 2, 3)]
AXIAL = ("Body_", "Head_", "Tail_")


def vec(value):
    return [round(float(component), 8) for component in value]


def collect(path):
    bpy.ops.wm.open_mainfile(filepath=str(path.resolve()))
    scene = bpy.context.scene
    arm = bpy.data.objects["CrimsonSpineBehemoth_Rig"]
    mesh = next(obj for obj in scene.objects if obj.type == "MESH" and any(
        modifier.type == "ARMATURE" and modifier.object == arm for modifier in obj.modifiers))
    scene.frame_set(1)
    bpy.context.view_layer.update()
    info = {
        "file": str(path),
        "bone_count": len(arm.data.bones),
        "mesh_vertices": len(mesh.data.vertices),
        "rest_matrices": {name: [round(float(value), 8) for row in arm.data.bones[name].matrix_local for value in row]
                          for name in CHAIN},
        "arm_matrix": [round(float(value), 8) for row in arm.matrix_world for value in row],
        "mesh_matrix": [round(float(value), 8) for row in mesh.matrix_world for value in row],
        "action": arm.animation_data.action.name if arm.animation_data and arm.animation_data.action else None,
        "actions": sorted(action.name for action in bpy.data.actions),
        "constraints": {name: [(item.name, item.type) for item in arm.pose.bones[name].constraints] for name in CHAIN},
        "camera": None,
        "frames": [],
    }
    group = mesh.vertex_groups[CHAIN[2]].index
    foot_indices = [vertex.index for vertex in mesh.data.vertices if any(
        weight.group == group and weight.weight >= 0.25 for weight in vertex.groups)]
    info["weighted_terminal_foot_vertices"] = len(foot_indices)
    if scene.camera:
        cam = scene.camera
        info["camera"] = {"name": cam.name, "type": cam.data.type,
                          "location": vec(cam.location), "rotation": vec(cam.rotation_euler),
                          "ortho_scale": float(cam.data.ortho_scale) if cam.data.type == "ORTHO" else None,
                          "resolution": [scene.render.resolution_x, scene.render.resolution_y,
                                         scene.render.resolution_percentage]}
    for frame in (1, 6, 12, 18, 24, 30, 32):
        if frame > scene.frame_end:
            continue
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        p = [arm.pose.bones[name] for name in CHAIN]
        hip, knee, ankle, tip = (arm.matrix_world @ value for value in
                                 (p[0].head, p[0].tail, p[1].tail, p[2].tail))
        body = {bone.name: vec((arm.matrix_world @ bone.head)) for bone in arm.pose.bones
                if bone.name.startswith(AXIAL)}
        evaluated = mesh.evaluated_get(bpy.context.evaluated_depsgraph_get())
        evaluated_mesh = evaluated.to_mesh()
        foot_floor = min((evaluated.matrix_world @ evaluated_mesh.vertices[index].co).z
                         for index in foot_indices)
        whole_floor = (min((evaluated.matrix_world @ vertex.co).z
                           for vertex in evaluated_mesh.vertices) if frame == 1 else None)
        evaluated.to_mesh_clear()
        info["frames"].append({"frame": frame, "hip": vec(hip), "knee": vec(knee),
                               "ankle": vec(ankle), "tip": vec(tip),
                               "weighted_foot_floor_z": round(foot_floor, 8),
                               "whole_mesh_floor_z": round(whole_floor, 8) if whole_floor is not None else None,
                               "foot_orientation": vec((arm.matrix_world @ p[2].matrix).to_quaternion()),
                               "body_heads": body})
    return info


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--original", type=Path, required=True)
    parser.add_argument("--planar", type=Path, required=True)
    parser.add_argument("--hybrid", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    if args.output.exists():
        raise RuntimeError("Refusing to overwrite an existing audit")
    files = {name: collect(path) for name, path in
             (("original", args.original), ("planar", args.planar), ("hybrid", args.hybrid))}
    ref = files["original"]
    differences = {}
    for name in ("planar", "hybrid"):
        test = files[name]
        differences[name] = {
            "rest_matrix_max_abs_delta": max(abs(a - b) for bone in CHAIN
                                              for a, b in zip(ref["rest_matrices"][bone],
                                                              test["rest_matrices"][bone])),
            "arm_matrix_max_abs_delta": max(abs(a-b) for a,b in zip(ref["arm_matrix"], test["arm_matrix"])),
            "mesh_matrix_max_abs_delta": max(abs(a-b) for a,b in zip(ref["mesh_matrix"], test["mesh_matrix"])),
            "original_actions_preserved": set(ref["actions"]).issubset(test["actions"]),
        }
    result = {"files": files, "differences": differences}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({"differences": differences,
                      "cameras": {name: item["camera"] for name,item in files.items()}}, indent=2))


if __name__ == "__main__":
    main()
