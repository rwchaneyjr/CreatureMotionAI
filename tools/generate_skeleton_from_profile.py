"""Generate a fresh armature from a mesh-derived anatomy profile."""
import argparse
import json
from pathlib import Path

import bpy
from mathutils import Vector


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--profile", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=args.input)
    profile = json.loads(Path(args.profile).read_text(encoding="utf-8"))
    # Make independence explicit: source armatures, actions, and animation
    # data are removed before creating any generated bones.
    for obj in list(bpy.context.scene.objects):
        if obj.type == "ARMATURE":
            bpy.data.objects.remove(obj, do_unlink=True)
    for action in list(bpy.data.actions):
        bpy.data.actions.remove(action)
    mesh = next((obj for obj in bpy.context.scene.objects if obj.type == "MESH"), None)
    if mesh is None:
        raise RuntimeError("The input asset contains no mesh")

    generated = bpy.data.armatures.new("CMAI_Generated_Skeleton")
    rig = bpy.data.objects.new("CMAI_Generated_Skeleton", generated)
    bpy.context.collection.objects.link(rig)
    bpy.context.view_layer.objects.active = rig
    rig.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    edit_bones = {}
    parts = profile["candidate_parts"]
    bones = [("Root", (0, 0, 0), (0, 0, 0.08), None),
             ("Torso", parts["body"][0]["bounds_min"], parts["body"][0]["bounds_max"], "Root"),
             ("Neck", parts["head_neck"][0]["anchor"], [parts["head_neck"][0]["anchor"][0], parts["head_neck"][0]["anchor"][1] + 0.08, parts["head_neck"][0]["anchor"][2]], "Torso"),
             ("Head", parts["head_neck"][0]["anchor"], [parts["head_neck"][0]["anchor"][0], parts["head_neck"][0]["anchor"][1] + 0.18, parts["head_neck"][0]["anchor"][2]], "Neck")]
    for limb in parts["limbs"]:
        bones.extend([(limb["name"] + "_upper", limb["hip"], limb["knee"], "Torso"),
                      (limb["name"] + "_lower", limb["knee"], limb["foot"], limb["name"] + "_upper")])
    tail = parts["tail"][0]
    bones.extend([("Tail_01", tail["start"], tail["end"], "Root")])
    for index in range(2, 5):
        previous = bones[-1]
        start = previous[2]
        end = [start[0], start[1] - abs(start[1] - tail["end"][1]) * 0.45, start[2] - 0.01]
        bones.append((f"Tail_{index:02d}", start, end, f"Tail_{index-1:02d}"))
    for name, head, tail_point, parent in bones:
        bone = generated.edit_bones.new(name)
        bone.name = name
        bone.head = Vector(head)
        bone.tail = Vector(tail_point)
        edit_bones[name] = bone
    for name, _, _, parent in bones:
        if parent in edit_bones:
            edit_bones[name].parent = edit_bones[parent]
    bpy.ops.object.mode_set(mode="OBJECT")
    rig["cmai_generated"] = True
    rig["cmai_profile"] = str(args.profile)
    rig["cmai_independent_of_source_armature"] = True
    rig["cmai_generation_method"] = "mesh_profile_template"
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=args.output)
    print(f"Generated {len(bones)} fresh bones from mesh profile: {args.output}")


if __name__ == "__main__":
    main()
