import bpy, json, sys
from pathlib import Path
from mathutils import Matrix, Vector, Quaternion

blend, report_path, out_blend, out_report = sys.argv[sys.argv.index('--')+1:]
bpy.ops.wm.open_mainfile(filepath=str(Path(blend).resolve()))
arm=bpy.data.objects['CrimsonSpineBehemoth_Rig']; mesh=bpy.data.objects['CrimsonSpineBehemoth_Mesh']
data=json.loads(Path(report_path).read_text()); names=data['bones']; axis=Vector(data['bend_axis']).normalized(); root=Vector(json.loads(Path(data['source_chain']).read_text())['chain_root_armature'])
scene=bpy.context.scene; scene.frame_set(1); bpy.context.view_layer.update()
baseline={n:(arm.pose.bones[n].rotation_mode, arm.pose.bones[n].rotation_quaternion.copy(), arm.pose.bones[n].matrix.copy()) for n in names}
rest={n:arm.data.bones[n].matrix_local.copy() for n in names}
deps=bpy.context.evaluated_depsgraph_get(); em=mesh.evaluated_get(deps); me=em.to_mesh(); baseverts=[v.co.copy() for v in me.vertices]; em.to_mesh_clear()
axis_local={n:(rest[n].to_3x3().inverted()@axis).normalized() for n in names}
def set_pose(qs):
    for n,(mode,q0,_) in baseline.items():
        p=arm.pose.bones[n]; p.rotation_mode='QUATERNION'; p.rotation_quaternion=q0.copy()
    for n,qv in zip(names,qs):
        p=arm.pose.bones[n]; dq=Quaternion(axis_local[n], float(qv)); p.rotation_quaternion=dq @ baseline[n][1]
    bpy.context.view_layer.update()
def measure(label, qs, expected_local):
    bpy.context.view_layer.update(); p=arm.pose.bones[names[-1]]
    foot=arm.matrix_world @ p.tail; joints=[]
    for n in names:
        pb=arm.pose.bones[n]; joints.append({'bone':n,'head':list(arm.matrix_world@pb.head),'tail':list(arm.matrix_world@pb.tail),'rotation_quaternion':list(pb.rotation_quaternion)})
    deps=bpy.context.evaluated_depsgraph_get(); em=mesh.evaluated_get(deps); me=em.to_mesh(); disp=max(((v.co-b).length for v,b in zip(me.vertices,baseverts)),default=0.0); em.to_mesh_clear()
    expected_world=arm.matrix_world @ (root + Vector(expected_local))
    return {'pose':label,'expected_foot_world':list(expected_world),'foot_world':list(foot),'foot_error':float((foot-expected_world).length),'mesh_max_displacement':float(disp),'joints':joints}
rows=[]; frames=[1,41,81]
for (name,entry),frame in zip([(x['name'],x) for x in data['targets']],frames):
    scene.frame_set(frame); set_pose(entry['q_revolute']); rows.append(measure(name,entry['q_revolute'],entry['target']))
scene.frame_set(1); set_pose(data['targets'][0]['q_revolute']);
scene.frame_start=1; scene.frame_end=81
arm['CMAI_Pinocchio_Application']='EXPERIMENTAL'; arm['CMAI_Pinocchio_Conversion']='rest-relative local axis quaternion'; arm['CMAI_Pinocchio_Status']='UNVERIFIED_BLENDER'
bpy.ops.wm.save_as_mainfile(filepath=str(Path(out_blend).resolve()))
Path(out_report).write_text(json.dumps({'status':'PINOCCHIO_BLENDER_APPLICATION_UNVERIFIED','source':report_path,'poses':rows,'note':'Applied to new copy; requires visual and endpoint comparison before acceptance.'},indent=2),encoding='utf-8')
print(json.dumps({'output_blend':out_blend,'output_report':out_report,'poses':len(rows)}))
