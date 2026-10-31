"""Automatically weight a mesh to the generated skeleton and render deformation tests."""
import argparse
from pathlib import Path

import bpy
from mathutils import Euler, Vector


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    bpy.ops.wm.open_mainfile(filepath=args.input)
    rig = bpy.data.objects.get("CMAI_Generated_Skeleton")
    mesh = next((obj for obj in bpy.data.objects if obj.type == "MESH"), None)
    if not rig or not mesh:
        raise RuntimeError("Generated rig or mesh not found")
    # Remove only generated binding state, then let Blender calculate weights
    # from bone envelopes/geometry. The source armature was deleted upstream.
    bpy.ops.object.select_all(action="DESELECT")
    mesh.select_set(True)
    bpy.context.view_layer.objects.active = mesh
    for modifier in list(mesh.modifiers):
        if modifier.type == "ARMATURE" and modifier.object == rig:
            mesh.modifiers.remove(modifier)
    for group in list(mesh.vertex_groups):
        mesh.vertex_groups.remove(group)
    rig.select_set(True)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.parent_set(type="ARMATURE_AUTO")
    modifier = next(item for item in mesh.modifiers if item.type == "ARMATURE" and item.object == rig)
    missing = [bone.name for bone in rig.data.bones if mesh.vertex_groups.get(bone.name) is None]
    rig["cmai_missing_vertex_groups"] = missing
    rig["cmai_binding_test"] = "automatic_weights"
    rig["cmai_weighted_bone_count"] = len(rig.data.bones) - len(missing)
    # Save a clean rest pose and one deterministic isolated rotation per limb.
    render_dir = Path(args.output).with_suffix("").parent / "screenshots"
    render_dir.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.render.resolution_x, scene.render.resolution_y = 960, 540
    camera_data = bpy.data.cameras.new("CMAI_Rig_Test_Camera")
    camera = bpy.data.objects.new("CMAI_Rig_Test_Camera", camera_data)
    bpy.context.collection.objects.link(camera)
    camera.location = (2.5, -3.0, 1.2)
    camera.rotation_euler = (Vector((0, 0, 0)) - camera.location).to_track_quat("-Z", "Y").to_euler()
    scene.camera = camera
    tests = []
    rig.show_in_front = True
    rig.display_type = "WIRE"
    # Armature objects are viewport-only in Workbench renders. Build a
    # temporary diagnostic line overlay so the saved rest-pose image actually
    # shows the generated bones inside the mesh.
    overlay_mesh = bpy.data.meshes.new("CMAI_Skeleton_Overlay_Mesh")
    overlay = bpy.data.objects.new("CMAI_Skeleton_Overlay", overlay_mesh)
    bpy.context.collection.objects.link(overlay)
    overlay_mesh.from_pydata([tuple(v) for bone in rig.data.bones for v in (bone.head_local, bone.tail_local)],
                             [], [(i * 2, i * 2 + 1) for i in range(len(rig.data.bones))])
    bevel = overlay.modifiers.new("Bone thickness", "BEVEL")
    bevel.width = 0.012
    bevel.segments = 2
    scene.render.filepath = str(render_dir / "skeleton_rest_pose.png")
    bpy.ops.render.render(write_still=True)
    tests.append({"bone": "__REST_SKELETON__", "rotation_z": 0.0,
                  "screenshot": scene.render.filepath})
    for bone in rig.pose.bones:
        if "_upper" not in bone.name and "_lower" not in bone.name:
            continue
        bone.rotation_mode = "XYZ"
        bone.rotation_euler = Euler((0.0, 0.0, 0.32), "XYZ")
        scene.render.filepath = str(render_dir / f"{bone.name.replace('.', '_')}.png")
        bpy.ops.render.render(write_still=True)
        tests.append({"bone": bone.name, "rotation_z": 0.32, "screenshot": scene.render.filepath})
        bone.rotation_euler = Euler((0.0, 0.0, 0.0), "XYZ")
    rig["cmai_deformation_tests"] = len(tests)
    rig["cmai_deformation_test_manifest"] = str(render_dir / "manifest.json")
    (render_dir / "manifest.json").write_text(__import__("json").dumps(tests, indent=2), encoding="utf-8")
    bpy.context.view_layer.objects.active = rig
    rig.select_set(True)
    bpy.ops.wm.save_as_mainfile(filepath=args.output)
    print(f"Bound {mesh.name} to {rig.name}; missing groups: {len(missing)}")


if __name__ == "__main__":
    main()
