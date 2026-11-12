import bpy, json
from mathutils import Vector
scene=bpy.context.scene
reg=bpy.data.objects.get('CMAI_FrontL_Diagnostic_Region')
arm=bpy.data.objects.get('CrimsonSpineBehemoth_Rig')
frames=[1,12,20]
vals={}
for f in frames:
    scene.frame_set(f); bpy.context.view_layer.update()
    ev=reg.evaluated_get(bpy.context.evaluated_depsgraph_get())
    vs=[(reg.matrix_world @ v.co).copy() for v in ev.data.vertices]
    vals[f]=vs
out={}
for f in frames[1:]:
    ds=[(a-b).length for a,b in zip(vals[f],vals[1])]
    out[str(f)]={'max_displacement':max(ds),'mean_displacement':sum(ds)/len(ds),'moved_vertices':sum(d>1e-5 for d in ds)}
json.dump(out,open('data/generated/frontL_three_pose_explicit/mesh_validation.json','w'),indent=2)
print(json.dumps(out))
