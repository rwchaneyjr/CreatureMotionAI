"""Read-only inventory of a Blender creature file for CMAI onboarding."""
import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector


def action_curve_count(action):
    count = 0
    try:
        for layer in action.layers:
            for strip in layer.strips:
                for bag in strip.channelbags:
                    count += len(bag.fcurves)
    except Exception:
        count = len(getattr(action, "fcurves", ()))
    return count


def main():
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if not args:
        raise SystemExit("Usage: blender --background --python inspect_creature_blend_readonly.py -- FILE.blend")
    src = Path(args[0]).resolve()
    bpy.ops.wm.open_mainfile(filepath=str(src))
    scene = bpy.context.scene

    armatures = []
    for arm in (o for o in scene.objects if o.type == "ARMATURE"):
        bones = []
        for bone in arm.data.bones:
            bones.append({
                "name": bone.name,
                "parent": bone.parent.name if bone.parent else None,
                "length": round(float(bone.length), 7),
                "deform": bool(bone.use_deform),
                "children": [child.name for child in bone.children],
            })
        action = arm.animation_data.action if arm.animation_data else None
        chain_bones = {}
        for side in ("L", "R"):
            for station in ("Front", "Rear"):
                label = f"Leg_{station}.{side}"
                chain_bones[label] = [f"{label}_{i:02d}" for i in (1, 2, 3)
                                      if arm.pose.bones.get(f"{label}_{i:02d}")]
        wings = {label: [b.name for b in arm.data.bones
                         if b.name.startswith(f"Wing.{side}") or b.name.startswith(f"WingRay") and b.name.endswith(f".{side}_01")]
                 for label, side in (("Wing.L", "L"), ("Wing.R", "R"))}
        motion_ranges = {}
        if action:
            first, last = int(action.frame_range[0]), int(action.frame_range[1])
            active_action = action
            for frame in range(first, last + 1):
                scene.frame_set(frame)
                bpy.context.view_layer.update()
                for label, names in {**chain_bones, **wings}.items():
                    for name in names:
                        pb = arm.pose.bones.get(name)
                        if not pb:
                            continue
                        row = motion_ranges.setdefault(name, {"head": [], "rotation": []})
                        row["head"].append(tuple((arm.matrix_world @ pb.head).to_tuple()))
                        row["rotation"].append(tuple(pb.rotation_quaternion if pb.rotation_mode == 'QUATERNION' else pb.rotation_euler))
            scene.frame_set(scene.frame_start)
            bpy.context.view_layer.update()
            motion_ranges = {
                name: {
                    "head_range_world": [round(max(v[i] for v in data["head"]) - min(v[i] for v in data["head"]), 6) for i in range(3)],
                    "rotation_component_ranges": [round(max(v[i] for v in data["rotation"]) - min(v[i] for v in data["rotation"]), 6) for i in range(len(data["rotation"][0]))],
                } for name, data in motion_ranges.items()
            }
        armatures.append({
            "name": arm.name,
            "bone_count": len(bones),
            "active_action": action.name if action else None,
            "bones": bones,
            "leg_chains": chain_bones,
            "wing_bones": wings,
            "active_action_motion_ranges": motion_ranges,
            "animation_data": bool(arm.animation_data),
        })

    meshes = []
    for mesh in (o for o in scene.objects if o.type == "MESH"):
        arm_mods = [m.object.name for m in mesh.modifiers if m.type == "ARMATURE" and m.object]
        groups = [g.name for g in mesh.vertex_groups]
        weighted = sum(1 for v in mesh.data.vertices if v.groups)
        world_corners = [(mesh.matrix_world @ Vector(c)).to_tuple() for c in mesh.bound_box]
        bounds = [[round(min(p[i] for p in world_corners), 6),
                   round(max(p[i] for p in world_corners), 6)] for i in range(3)]
        meshes.append({
            "name": mesh.name,
            "vertices": len(mesh.data.vertices),
            "polygons": len(mesh.data.polygons),
            "armature_modifiers": arm_mods,
            "vertex_group_count": len(groups),
            "weighted_vertices": weighted,
            "bounds_world": bounds,
        })

    actions = []
    for action in bpy.data.actions:
        actions.append({
            "name": action.name,
            "frame_range": [round(float(x), 4) for x in action.frame_range],
            "curve_count": action_curve_count(action),
            "users": action.users,
        })
    result = {
        "source": str(src),
        "scene_fps": scene.render.fps / scene.render.fps_base,
        "frame_range": [scene.frame_start, scene.frame_end],
        "armatures": armatures,
        "meshes": meshes,
        "actions": actions,
        "status": "READ_ONLY_INSPECTION",
    }
    if "--summary" in args:
        summary = {k: result[k] for k in ("source", "scene_fps", "frame_range", "meshes", "actions", "status")}
        summary["armatures"] = [{k: a[k] for k in ("name", "bone_count", "active_action", "leg_chains", "wing_bones", "active_action_motion_ranges")}
                                for a in armatures]
        print("CMAI_READ_ONLY_INSPECTION=" + json.dumps(summary, separators=(",", ":")))
    else:
        print("CMAI_READ_ONLY_INSPECTION=" + json.dumps(result, separators=(",", ":")))


if __name__ == "__main__":
    main()
