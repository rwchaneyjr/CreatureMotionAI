import bpy
import os

blend_in = os.environ["CMAI_MOCAP_BLEND_IN"]
blend_out = os.environ["CMAI_MOCAP_BLEND_OUT"]
bvh_path = os.environ["CMAI_MOCAP_BVH"]

bpy.ops.wm.open_mainfile(filepath=blend_in)
before = {o.name for o in bpy.data.objects}
bpy.ops.import_anim.bvh(filepath=bvh_path, global_scale=float(os.environ.get("CMAI_MOCAP_IMPORT_SCALE", "1.0")), use_cyclic=False,
                        update_scene_fps=False, update_scene_duration=False)
after = [o for o in bpy.data.objects if o.name not in before and o.type == "ARMATURE"]
if not after:
    raise RuntimeError("MoCapAnything BVH import created no armature")

imported = after[-1]
imported.name = "MoCapAnything_Balisk_24f_BVH"
for o in bpy.context.scene.objects:
    o.select_set(False)
imported.select_set(True)
bpy.context.view_layer.objects.active = imported

bpy.context.scene.frame_start = 1
bpy.context.scene.frame_end = 24
bpy.ops.wm.save_as_mainfile(filepath=blend_out)
print({"imported_armature": imported.name, "bones": len(imported.data.bones), "out": blend_out})
