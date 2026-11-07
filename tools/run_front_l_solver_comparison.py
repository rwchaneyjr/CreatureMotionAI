import argparse, subprocess, json, sys
from pathlib import Path

def run(blender, source, mode, output, report, contact_bias=0.0):
    expr = f'''import bpy, json, math
from mathutils import Vector
from pathlib import Path
from creature_motion_ai.ik_step import solve_rest_relative_two_link, world_direction_pose_matrix, restore_terminal_foot_world_orientation
bpy.ops.wm.open_mainfile(filepath=r"{Path(source).resolve()}")
s=bpy.context.scene; s.frame_start=1; s.frame_end=24; s.render.fps=24
arm=next(o for o in s.objects if o.type=='ARMATURE'); mesh=next(o for o in s.objects if o.type=='MESH' and not o.name.startswith('CMAI_'))
names=['Leg_Front.L_01','Leg_Front.L_02','Leg_Front.L_03']; pbs=[arm.pose.bones[n] for n in names]
for pb in arm.pose.bones:
    for c in list(pb.constraints): pb.constraints.remove(c)
for o in list(bpy.data.objects):
    if o.get('cmai_proxy') or o.name.startswith(('CMAI_PROXY','CMAI_')): o.hide_viewport=True; o.hide_render=True
s.frame_set(1); bpy.context.view_layer.update()
def W(pb,tail=False): return arm.matrix_world @ (pb.tail if tail else pb.head)
hip=W(pbs[0]); knee=W(pbs[0],True); ankle=W(pbs[1],True); foot=W(pbs[2],True); upper=(knee-hip).length; lower=(ankle-knee).length; bend=(knee-hip).cross(ankle-hip).normalized(); rest={{n:arm.matrix_world@arm.pose.bones[n].matrix.copy() for n in names}}
target_obj=None; pole_obj=None; con=None
if '{mode}'=='blender_ik':
    target_obj=bpy.data.objects.new('CMAI_FrontL_Test_Target',None); s.collection.objects.link(target_obj); pole_obj=bpy.data.objects.new('CMAI_FrontL_Test_Pole',None); s.collection.objects.link(pole_obj); pole_dir=bend.cross((knee-hip).normalized()).normalized(); pole_obj.location=knee+pole_dir*.22; con=pbs[2].constraints.new('IK'); con.name='CMAI_FrontL_Builtin_IK'; con.target=target_obj; con.pole_target=pole_obj; con.chain_count=3; con.influence=1.0
act=bpy.data.actions.new('CMAI_FrontL_{mode}_24F'); arm.animation_data_create(); arm.animation_data.action=act
rows=[]
for f in range(1,25):
    q=(f-1)/23.0; phase=math.sin(2*math.pi*q); lift=max(0.0,math.sin(math.pi*q))*(.008+{contact_bias}); desired=foot+Vector((0.0,phase*.012,lift))
    if target_obj: target_obj.location=desired; target_obj.keyframe_insert('location',frame=f)
    solve_target=ankle+Vector((0.0,phase*.012,lift))
    if '{mode}'=='custom':
        sol=solve_rest_relative_two_link(hip,solve_target,upper,lower,bend,min_knee_angle=math.radians(12)); status=sol.get('status')
        if status=='PASS':
            b1,b2=pbs[0],pbs[1]; b1.matrix=arm.matrix_world.inverted()@world_direction_pose_matrix(rest[names[0]],hip,hip,sol['knee'],knee); bpy.context.view_layer.update(); b2.matrix=arm.matrix_world.inverted()@world_direction_pose_matrix(rest[names[1]],knee,sol['knee'],sol['foot'],ankle); bpy.context.view_layer.update(); restore_terminal_foot_world_orientation(arm,names[2],rest[names[2]],arm.matrix_world@b2.tail); bpy.context.view_layer.update()
    elif '{mode}'=='fk':
        sol=solve_rest_relative_two_link(hip,solve_target,upper,lower,bend,min_knee_angle=math.radians(12)); status=sol.get('status')
        if status=='PASS':
            b1,b2=pbs[0],pbs[1]; b1.matrix=arm.matrix_world.inverted()@world_direction_pose_matrix(rest[names[0]],hip,hip,sol['knee'],knee); bpy.context.view_layer.update(); b2.matrix=arm.matrix_world.inverted()@world_direction_pose_matrix(rest[names[1]],knee,sol['knee'],sol['foot'],ankle); bpy.context.view_layer.update(); restore_terminal_foot_world_orientation(arm,names[2],rest[names[2]],arm.matrix_world@b2.tail); bpy.context.view_layer.update()
    else: status='PASS'
    for pb in pbs:
        pb.rotation_mode='QUATERNION'; pb.keyframe_insert('rotation_quaternion',frame=f,group=pb.name)
    s.frame_set(f); bpy.context.view_layer.update(); actual=W(pbs[2],True); rows.append({{'frame':f,'status':status,'target_error':(actual-desired).length,'foot_displacement':(actual-foot).length}})
s['CMAI_test_method']='{mode}'; bpy.ops.wm.save_as_mainfile(filepath=r"{Path(output).resolve()}")
Path(r"{Path(report).resolve()}").write_text(json.dumps({{'status':'TEST_CREATED','method':'{mode}','frames':rows,'chain':names,'other_legs_animated':False}},indent=2),encoding='utf-8')
'''
    subprocess.run([blender,'--background','--python-expr',expr],check=True)

if __name__=='__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('--blender',required=True); ap.add_argument('--source',required=True); ap.add_argument('--out-dir',required=True); ap.add_argument('--contact-bias',type=float,default=0.0); a=ap.parse_args(); d=Path(a.out_dir); d.mkdir(parents=True,exist_ok=True)
    for mode in ('custom','blender_ik','fk'):
        suffix='_corrected' if a.contact_bias else ''
        run(a.blender,a.source,mode,d/f'front_l_{mode}_24f{suffix}.blend',d/f'front_l_{mode}_report{suffix}.json',a.contact_bias)
    print('CREATED',d)
