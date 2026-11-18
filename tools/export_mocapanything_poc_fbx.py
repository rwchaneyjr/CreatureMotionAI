import bpy
import os
from pathlib import Path

out = Path(os.environ.get('CMAI_EXPORT_PATH', 'mocapanything_poc_balisk.fbx'))
out.parent.mkdir(parents=True, exist_ok=True)
bpy.ops.object.select_all(action='DESELECT')
armatures = [o for o in bpy.data.objects if o.type == 'ARMATURE']
meshes = [o for o in bpy.data.objects if o.type == 'MESH']
for obj in armatures + meshes:
    obj.select_set(True)
if armatures:
    bpy.context.view_layer.objects.active = armatures[0]
bpy.ops.export_scene.fbx(filepath=str(out), use_selection=True, add_leaf_bones=False,
                         bake_anim=False, object_types={'ARMATURE', 'MESH'},
                         apply_scale_options='FBX_SCALE_NONE')
print(f'CMAI_POC_FBX={out}')
