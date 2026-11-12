import bpy, json, math, sys
from pathlib import Path
from mathutils import Vector, Matrix, Quaternion

blend, out = sys.argv[sys.argv.index('--') + 1:]
bpy.ops.wm.open_mainfile(filepath=str(Path(blend).resolve()))
s=bpy.context.scene; arm=bpy.data.objects['CrimsonSpineBehemoth_Rig']
names=['Leg_Front.L_01','Leg_Front.L_02','Leg_Front.L_03']
s.frame_set(1); bpy.context.view_layer.update()
baseline={p.name:p.matrix.copy() for p in arm.pose.bones}
data=json.loads(Path('data/generated/ikpy_frontL_chain.json').read_text())
root=Vector(data['chain_root_armature']); heads=[root+Vector(b['head_armature'])-Vector(data['chain_root_armature']) for b in data['bones']]
tail=Vector(data['bones'][-1]['tail_armature'])
segments=[Vector(data['bones'][i]['tail_armature'])-Vector(data['bones'][i]['head_armature']) for i in range(3)]
n=segments[0].cross(segments[1]).normalized(); angle=0.1

def reset():
    for n,m in baseline.items(): arm.pose.bones[n].matrix=m.copy()
    bpy.context.view_layer.update()

def pos(pb): return arm.matrix_world @ pb.head, arm.matrix_world @ pb.tail
results=[]
for i,name in enumerate(names):
    reset(); pb=arm.pose.bones[name]; rb=arm.data.bones[name]
    # IKPy axis expressed in this bone's rest-local coordinates.
    local_axis=rb.matrix_local.to_3x3().inverted() @ n
    local_axis.normalize()
    q=Quaternion(local_axis, angle)
    if pb.rotation_mode=='QUATERNION': pb.rotation_quaternion=q
    else: pb.rotation_mode='QUATERNION'; pb.rotation_quaternion=q
    bpy.context.view_layer.update()
    h,t=pos(pb)
    results.append({'bone':name,'angle_rad':angle,'ik_axis_armature':list(n),'ik_axis_local':list(local_axis),'head_world':list(h),'tail_world':list(t),'rest_head_world':list(arm.matrix_world @ (baseline[name] @ Vector((0,0,0)))),'rest_tail_world':list(arm.matrix_world @ (baseline[name] @ Vector((0,arm.data.bones[name].length,0))))})
reset()
payload={'angle_rad':angle,'axis_definition':'IKPy bend axis converted through each bone rest matrix','results':results}
Path(out).write_text(json.dumps(payload,indent=2)); print(json.dumps(payload,indent=2))
