import bpy, json, sys
from pathlib import Path
from mathutils import Vector, Quaternion

blend, report, out_blend, out_report = sys.argv[sys.argv.index('--') + 1:]
bpy.ops.wm.open_mainfile(filepath=str(Path(blend).resolve()))
s=bpy.context.scene; arm=bpy.data.objects['CrimsonSpineBehemoth_Rig']
data=json.loads(Path(report).read_text()); names=data['bones']; test=next(x for x in data['tests'] if x['name']=='forward_up')
s.frame_set(1); bpy.context.view_layer.update(); base={p.name:p.matrix.copy() for p in arm.pose.bones}
for n,m in base.items(): arm.pose.bones[n].matrix=m.copy()
for i,n in enumerate(names):
    pb=arm.pose.bones[n]; rb=arm.data.bones[n]
    axis=(rb.matrix_local.to_3x3().inverted() @ Vector(data['bend_plane_normal'])).normalized()
    pb.rotation_mode='QUATERNION'; pb.rotation_quaternion=Quaternion(axis,-float(test['solution'][i+1]))
s.frame_set(12); bpy.context.view_layer.update()
res=[]
root=Vector(data['chain_root_armature'])
for i,n in enumerate(names):
    p=arm.pose.bones[n]
    exp=root+Vector((test['joint_matrices'][i][0][3],test['joint_matrices'][i][1][3],test['joint_matrices'][i][2][3]))
    exp_tail=root+Vector((test['joint_matrices'][i+1][0][3],test['joint_matrices'][i+1][1][3],test['joint_matrices'][i+1][2][3]))
    res.append({'bone':n,'head_error':float((p.head-exp).length),'tail_error':float((p.tail-exp_tail).length),'angle':float(test['solution'][i+1])})
bpy.ops.wm.save_as_mainfile(filepath=str(Path(out_blend).resolve()))
Path(out_report).write_text(json.dumps({'results':res},indent=2))
print(json.dumps(res,indent=2))
