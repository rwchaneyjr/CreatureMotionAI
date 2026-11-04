"""Create a 24-frame in-place eight-legged walk from the original standing rig."""
import argparse, json, subprocess
from pathlib import Path

def main():
    p=argparse.ArgumentParser(); p.add_argument('--blend',required=True); p.add_argument('--output',required=True); p.add_argument('--report',required=True); p.add_argument('--blender',required=True); a=p.parse_args()
    expr=f"""
import bpy, math, json
from mathutils import Vector
bpy.ops.wm.open_mainfile(filepath=r'{Path(a.blend).resolve()}')
s=bpy.context.scene; s.frame_start=1; s.frame_end=24; s.render.fps=24
arm=next(o for o in bpy.data.objects if o.type=='ARMATURE')
if len(arm.data.bones)!=38: raise RuntimeError('Expected original 38-bone rig')
for pb in arm.pose.bones:
    for c in list(pb.constraints): pb.constraints.remove(c)
for act in list(bpy.data.actions):
    if act.users==0: bpy.data.actions.remove(act)
action=bpy.data.actions.new('CMAI_Clean_Procedural_Walk_24F'); action.use_fake_user=True; arm.animation_data_create(); arm.animation_data.action=action
legs=['Leg_Front.L','Leg_Front.R','Leg_MidFront.L','Leg_MidFront.R','Leg_MidRear.L','Leg_MidRear.R','Leg_Rear.L','Leg_Rear.R']
items=[]
for idx,name in enumerate(legs):
    upper=arm.pose.bones[name+'_01']; lower=arm.pose.bones[name+'_02']; foot=arm.pose.bones[name+'_03']; hip=arm.matrix_world@upper.head; knee=arm.matrix_world@upper.tail; ankle=arm.matrix_world@lower.tail; base=arm.matrix_world@foot.tail
    incoming=(knee-hip).normalized(); outgoing=(base-knee).normalized(); plane=incoming.cross(outgoing)
    if plane.length<1e-6: plane=Vector((0,0,1))
    pole_dir=plane.normalized().cross(incoming).normalized(); target=bpy.data.objects.new('CMAI_Walk_Target_'+name,None); target.empty_display_type='SPHERE'; target.empty_display_size=.035; target.location=base; s.collection.objects.link(target)
    pole=bpy.data.objects.new('CMAI_Walk_Pole_'+name,None); pole.empty_display_type='CUBE'; pole.empty_display_size=.025; pole.location=knee+pole_dir*.22; s.collection.objects.link(pole)
    con=foot.constraints.new('IK'); con.name='CMAI_Walk_IK_'+name; con.target=target; con.pole_target=pole; con.chain_count=3; con.influence=1.0
    items.append((name,target,base,idx))
for f in range(1,25):
    phase=(f-1)/24.0*math.tau
    for name,target,base,idx in items:
        # Four-phase alternating gait: at least four feet remain in support.
        ph=phase+idx*math.pi/4.0; swing=max(0.0,math.sin(ph)); stride=math.sin(ph)*.055; lift=(swing*swing)*.045
        target.location=base+Vector((0.0,stride,lift)); target.keyframe_insert('location',frame=f)
s.frame_set(1); s['CMAI_walk_validation']='procedural_24_frame_pending_physical_review'; s['CMAI_original_rest_preserved']=True
bpy.ops.wm.save_as_mainfile(filepath=r'{Path(a.output).resolve()}')
print(json.dumps({{'action':action.name,'frames':24,'legs':8,'constraints':8,'chain_count':3,'foot_lift_max':.045,'source':r'{Path(a.blend).resolve()}'}}))
"""
    r=subprocess.run([a.blender,'--background','--python-expr',expr],capture_output=True,text=True,check=True)
    data=json.loads(next(x for x in reversed(r.stdout.splitlines()) if x.strip().startswith('{'))); data.update({'status':'procedural_walk_test_pending_validation','output':str(Path(a.output).resolve()),'report':str(Path(a.report).resolve())}); Path(a.report).write_text(json.dumps(data,indent=2)); print(json.dumps(data,indent=2))
if __name__=='__main__': main()
