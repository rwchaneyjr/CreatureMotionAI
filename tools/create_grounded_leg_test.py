"""Safe eight-leg IK contact test from the original standing pose."""
import argparse, subprocess, json
from pathlib import Path

def main():
    p=argparse.ArgumentParser(); p.add_argument('--blend',required=True); p.add_argument('--output',required=True); p.add_argument('--blender',required=True); p.add_argument('--report',required=True); a=p.parse_args()
    expr=f"""
import bpy, math, json
from mathutils import Vector
bpy.ops.wm.open_mainfile(filepath=r'{Path(a.blend).resolve()}')
scene=bpy.context.scene; scene.frame_start=1; scene.frame_end=24; scene.render.fps=24
arm=next(o for o in bpy.data.objects if o.type=='ARMATURE'); scene.frame_set(1)
for p in arm.pose.bones:
    for c in list(p.constraints): p.constraints.remove(c)
act=bpy.data.actions.new('CMAI_Grounded_EightLeg_Test_1s'); arm.animation_data_create(); arm.animation_data.action=act
legs=['Leg_Front.L','Leg_Front.R','Leg_MidFront.L','Leg_MidFront.R','Leg_MidRear.L','Leg_MidRear.R','Leg_Rear.L','Leg_Rear.R']
targets=[]; baseline={{}}
for idx,name in enumerate(legs):
    upper=arm.pose.bones[name+'_01']; lower=arm.pose.bones[name+'_02']; foot=arm.pose.bones[name+'_03']
    # Lower-bone tail is the IK endpoint; this avoids the earlier knee-target bug.
    end=arm.matrix_world @ lower.tail; base=end.copy(); baseline[name]=tuple(base)
    td=bpy.data.objects.new('CMAI_FootTarget_'+name,None); td.empty_display_type='SPHERE'; td.empty_display_size=.035; td.location=base; td.color=(0.1,0.8,0.2,1); scene.collection.objects.link(td)
    pd=bpy.data.objects.new('CMAI_Pole_'+name,None); pd.empty_display_type='CUBE'; pd.empty_display_size=.025
    # Pole remains on the original knee-bend side, offset conservatively.
    knee=arm.matrix_world @ upper.tail; pd.location=knee+Vector((-0.18,0,0.18)); pd.color=(0.9,0.2,0.1,1); scene.collection.objects.link(pd)
    c=upper.constraints.new('IK'); c.name='CMAI_Grounded_IK_'+name; c.target=td; c.pole_target=pd; c.chain_count=2; c.pole_angle=0.0; c.influence=1.0
    targets.append((name,td,base))
for frame in range(1,25):
    phase=(frame-1)/24.0*2*math.pi
    for idx,(name,td,base) in enumerate(targets):
        # Alternating phase keeps at least four support legs planted.
        ph=phase + idx*math.pi/4.0
        swing=max(0.0,math.sin(ph))
        stride=math.sin(ph)*0.035
        lift=swing*0.028
        td.location=Vector((base.x,base.y+stride,base.z+lift))
        td.keyframe_insert('location',frame=frame)
    # Keep root motion bounded and independent from leg-root keys.
    root=arm.pose.bones.get('Root'); root.location=(0,math.sin(phase)*0.015,0); root.keyframe_insert('location',frame=frame,group='Root')
scene.frame_set(1); bpy.ops.wm.save_as_mainfile(filepath=r'{Path(a.output).resolve()}')
print(json.dumps({{'action':'CMAI_Grounded_EightLeg_Test_1s','frames':24,'ik_constraints':len(targets),'direct_leg_keys':False,'target_baseline':'lower-bone-tail','foot_lift_max':0.028}}))
"""
    r=subprocess.run([a.blender,'--background','--python-expr',expr],capture_output=True,text=True,check=True)
    data={}
    for line in reversed(r.stdout.splitlines()):
        if line.strip().startswith('{'): data=json.loads(line); break
    data.update({'input':str(Path(a.blend).resolve()),'output':str(Path(a.output).resolve()),'status':'grounded_ik_test_not_reference_validated'})
    Path(a.report).write_text(json.dumps(data,indent=2),encoding='utf-8'); print(json.dumps(data,indent=2))
if __name__=='__main__': main()
