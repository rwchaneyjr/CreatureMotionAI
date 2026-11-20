import argparse
import math
import os

import bpy
from mathutils import Vector


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--frame", type=int, default=1)
    parser.add_argument("--action", default="FLAP")
    parser.add_argument("--camera-side", type=int, choices=(-1, 1), default=-1,
                        help="View from the negative or positive armature X side")
    args = parser.parse_args(bpy_args())

    scene = bpy.context.scene
    rig = bpy.data.objects.get("CrimsonWingedDragon_Rig")
    if rig is None:
        raise RuntimeError("CrimsonWingedDragon_Rig not found")
    mesh_objects = [o for o in scene.objects if o.type == "MESH" and any(m.type == "ARMATURE" and m.object == rig for m in o.modifiers)]
    if not mesh_objects:
        raise RuntimeError("No mesh skinned to CrimsonWingedDragon_Rig")

    old_camera = scene.camera
    old_frame = scene.frame_current
    old_path = scene.render.filepath
    old_res = (scene.render.resolution_x, scene.render.resolution_y, scene.render.resolution_percentage)
    old_transparent = scene.render.film_transparent
    old_engine = scene.render.engine
    old_action = rig.animation_data.action if rig.animation_data else None
    old_slot = rig.animation_data.action_slot if rig.animation_data and hasattr(rig.animation_data, "action_slot") else None

    action = bpy.data.actions.get(args.action)
    if action and rig.animation_data:
        rig.animation_data.action = action
        if hasattr(rig.animation_data, "action_slot") and len(action.slots):
            try:
                rig.animation_data.action_slot = action.slots[0]
            except Exception:
                pass

    # Compute bounds from evaluated skinned geometry in the chosen pose.
    # Action frame_range values are floats in newer Blender versions, while
    # Scene.frame_set expects an integer frame number.
    requested_frame = int(args.frame)
    action_frame = int(max(action.frame_range[0], min(requested_frame, action.frame_range[1]))) if action else requested_frame
    scene.frame_set(action_frame)
    depsgraph = bpy.context.evaluated_depsgraph_get()
    points = []
    for obj in mesh_objects:
        evaluated = obj.evaluated_get(depsgraph)
        mesh = evaluated.to_mesh()
        points.extend(evaluated.matrix_world @ v.co for v in mesh.vertices)
        evaluated.to_mesh_clear()
    lo = Vector(tuple(min(p[i] for p in points) for i in range(3)))
    hi = Vector(tuple(max(p[i] for p in points) for i in range(3)))
    center = (lo + hi) * 0.5
    size = hi - lo

    cam_data = bpy.data.cameras.new("CMAI_TempSideCamera")
    cam_data.type = "ORTHO"
    # ortho_scale is the horizontal span; compensate for the landscape render
    # so the full tail and raised wing tips remain inside the vertical frame.
    cam_data.ortho_scale = max(size.y, size.z) * 1.85
    cam = bpy.data.objects.new("CMAI_TempSideCamera", cam_data)
    scene.collection.objects.link(cam)
    cam.location = center + Vector((args.camera_side * max(size.x, size.y, size.z) * 3.2, 0.0, 0.0))
    direction = center - cam.location
    cam.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    scene.camera = cam

    temp_lights = []
    for name, offset, power, size_light in (
        ("CMAI_Key", Vector((-2.8, 0.0, 3.4)), 1500.0, 4.0),
        ("CMAI_Fill", Vector((-2.0, 2.0, 0.3)), 800.0, 3.0),
        ("CMAI_Rim", Vector((2.5, 0.0, 2.2)), 1200.0, 3.0),
    ):
        data = bpy.data.lights.new(name, "AREA")
        data.energy = power
        data.shape = "DISK"
        data.size = size_light
        light = bpy.data.objects.new(name, data)
        scene.collection.objects.link(light)
        light.location = center + offset
        light.rotation_euler = (center - light.location).to_track_quat("-Z", "Y").to_euler()
        temp_lights.append((light, data))

    # Temporary studio world lighting, without changing model materials.
    world = scene.world
    if world:
        world.use_nodes = True
        world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.34, 0.38, 0.44, 1.0)
        world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.65
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 1400
    scene.render.resolution_y = 850
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = False
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = os.path.abspath(args.output)
    scene.render.resolution_percentage = 100
    scene.render.use_file_extension = True
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.filepath = os.path.abspath(args.output)
    scene.frame_set(action_frame)
    bpy.ops.render.render(write_still=True)

    scene.camera = old_camera
    scene.frame_set(old_frame)
    scene.render.filepath = old_path
    scene.render.resolution_x, scene.render.resolution_y, scene.render.resolution_percentage = old_res
    scene.render.film_transparent = old_transparent
    scene.render.engine = old_engine
    if rig.animation_data:
        rig.animation_data.action = old_action
        if old_slot is not None and hasattr(rig.animation_data, "action_slot"):
            try:
                rig.animation_data.action_slot = old_slot
            except Exception:
                pass
    bpy.data.objects.remove(cam, do_unlink=True)
    bpy.data.cameras.remove(cam_data)
    for light, data in temp_lights:
        bpy.data.objects.remove(light, do_unlink=True)
        bpy.data.lights.remove(data)
    print(f"DRAGON_SIDE_STILL output={args.output} frame={args.frame} action={args.action} bounds={tuple(lo)}..{tuple(hi)}")


def bpy_args():
    import sys
    return sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


if __name__ == "__main__":
    main()
