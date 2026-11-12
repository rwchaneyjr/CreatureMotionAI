import bpy, json, sys, math
from pathlib import Path
from mathutils import Vector, Quaternion

args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else sys.argv[1:]
blend, chain_path, report_path, out_blend, out_report, out_dir = args[:6]
bpy.ops.wm.open_mainfile(filepath=str(Path(blend).resolve()))
arm=bpy.data.objects['CrimsonSpineBehemoth_Rig']; mesh=bpy.data.objects['CrimsonSpineBehemoth_Mesh']
chain=json.loads(Path(chain_path).read_text()); reach=json.loads(Path(report_path).read_text())
names=[b['name'] for b in chain['bones']]; root=Vector(chain['chain_root_armature'])
scene=bpy.context.scene; scene.frame_set(1); bpy.context.view_layer.update()
baseline={n:(arm.pose.bones[n].rotation_mode, arm.pose.bones[n].rotation_quaternion.copy()) for n in names}
rest={n:arm.data.bones[n].matrix_local.copy() for n in names}
# Blender pose-bone quaternion channels are bone-local.  Pinocchio's
# MidRear.L chain was constructed with a revolute X axis in each joint's
# parent-relative rest basis; do not transform one shared world axis into
# every bone basis.
axis_local={n:Vector((1,0,0)) for n in names}
deps=bpy.context.evaluated_depsgraph_get(); em=mesh.evaluated_get(deps); me=em.to_mesh(); base=[v.co.copy() for v in me.vertices]; em.to_mesh_clear()
def reset():
    for n,(mode,q) in baseline.items():
        p=arm.pose.bones[n]; p.rotation_mode='QUATERNION'; p.rotation_quaternion=q.copy()
def apply(qs):
    reset()
    for n,qv in zip(names,qs): arm.pose.bones[n].rotation_quaternion=Quaternion(axis_local[n],float(qv)) @ baseline[n][1]
    bpy.context.view_layer.update()
def measure(label, entry, filename):
    apply(entry['q_revolute']); bpy.context.view_layer.update(); pbs=[arm.pose.bones[n] for n in names]
    foot=arm.matrix_world@pbs[-1].tail; expected=arm.matrix_world@(root+Vector(entry['target']))
    deps=bpy.context.evaluated_depsgraph_get(); em=mesh.evaluated_get(deps); me=em.to_mesh(); disp=max((v.co-b).length for v,b in zip(me.vertices,base)); em.to_mesh_clear()
    joints=[{'name':n,'head':list(arm.matrix_world@p.head),'tail':list(arm.matrix_world@p.tail),'quat':list(p.rotation_quaternion)} for n,p in zip(names,pbs)]
    scene.render.filepath=str(Path(out_dir)/filename); bpy.ops.render.render(write_still=True)
    return {'label':label,'target_world':list(expected),'foot_world':list(foot),'foot_error':float((foot-expected).length),'mesh_max_displacement':float(disp),'joints':joints}
tests=[x for x in reach['tests'] if x['name'] in ('rest','lift','forward_up')]
rows=[measure(x['name'],x,{'rest':'midrear_rest.png','lift':'midrear_lift.png','forward_up':'midrear_forward_up.png'}[x['name']]) for x in tests]
reset(); scene.frame_set(1); bpy.context.view_layer.update();
arm.animation_data_create(); act=bpy.data.actions.new('CMAI_MidRearL_Pinocchio_Diagnostic'); arm.animation_data.action=act
for n in names:
    p=arm.pose.bones[n]; p.rotation_mode='QUATERNION'; p.rotation_quaternion=baseline[n][1]; p.keyframe_insert('rotation_quaternion',frame=1); p.keyframe_insert('rotation_quaternion',frame=24)
lift=next(x for x in tests if x['name']=='lift'); apply(lift['q_revolute'])
for n in names: arm.pose.bones[n].keyframe_insert('rotation_quaternion',frame=12)
reset(); scene.frame_set(1); bpy.context.view_layer.update()
scene['CMAI_Pinocchio_MidRearL_Status']='UNVERIFIED_BLENDER_DIAGNOSTIC'; bpy.ops.wm.save_as_mainfile(filepath=str(Path(out_blend).resolve()))
Path(out_report).write_text(json.dumps({'status':'MIDREARL_BLENDER_APPLICATION_UNVERIFIED','chain':chain_path,'pinocchio_report':report_path,'poses':rows,'action':act.name,'note':'Temporary diagnostic; no original file modified.'},indent=2))
print(json.dumps({'out_blend':out_blend,'out_report':out_report,'poses':rows},indent=2))
