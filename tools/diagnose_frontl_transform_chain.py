import bpy, json, sys
from pathlib import Path
from mathutils import Matrix, Vector

blend, ik_report, blender_report, out = sys.argv[sys.argv.index('--') + 1:]
bpy.ops.wm.open_mainfile(filepath=str(Path(blend).resolve()))
arm=bpy.data.objects['CrimsonSpineBehemoth_Rig']; s=bpy.context.scene
ik=json.loads(Path(ik_report).read_text()); br=json.loads(Path(blender_report).read_text())
names=ik['bones']; root=Vector(ik['chain_root_armature'])
test=next(x for x in ik['tests'] if x['name']=='forward_up')
actual=next(x for x in br['results'] if x['pose']=='forward_up')
s.frame_set(12); bpy.context.view_layer.update()
rows=[]
for i,n in enumerate(names):
    p=arm.pose.bones[n]; rest=arm.data.bones[n].matrix_local
    ik_head=root+Vector((test['joint_matrices'][i][0][3],test['joint_matrices'][i][1][3],test['joint_matrices'][i][2][3]))
    ik_tail=root+Vector((test['joint_matrices'][i+1][0][3],test['joint_matrices'][i+1][1][3],test['joint_matrices'][i+1][2][3]))
    rows.append({'bone':n,'parent':arm.data.bones[n].parent.name if arm.data.bones[n].parent else None,'ik_head':list(ik_head),'ik_tail':list(ik_tail),'blender_head':list(p.head),'blender_tail':list(p.tail),'head_error':float((p.head-ik_head).length),'tail_error':float((p.tail-ik_tail).length),'rest_matrix':[[float(v) for v in r] for r in rest],'pose_matrix':[[float(v) for v in r] for r in p.matrix]})
payload={'blend':str(Path(blend).resolve()),'frame':12,'results':rows,'ik_target_error':actual.get('target_error_armature'),'first_position_divergence':next((r['bone'] for r in rows if r['head_error']>1e-4 or r['tail_error']>1e-4),'none')}
Path(out).write_text(json.dumps(payload,indent=2)); print(json.dumps(payload,indent=2))
