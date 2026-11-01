"""Validate one-leg-at-a-time IK against the original standing pose."""
import argparse, json, subprocess
from pathlib import Path

def main():
    p=argparse.ArgumentParser(); p.add_argument('--blend',required=True); p.add_argument('--output',required=True); p.add_argument('--report',required=True); p.add_argument('--render',required=True); p.add_argument('--blender',required=True); a=p.parse_args()
    expr=f"""
import bpy, json, math
from mathutils import Vector
bpy.ops.wm.open_mainfile(filepath=r'{Path(a.blend).resolve()}')
scene=bpy.context.scene; scene.frame_set(1); arm=next(o for o in bpy.data.objects if o.type=='ARMATURE')
legs=['Leg_Front.L','Leg_Front.R','Leg_MidFront.L','Leg_MidFront.R','Leg_MidRear.L','Leg_MidRear.R','Leg_Rear.L','Leg_Rear.R']
for pb in arm.pose.bones:
    for c in list(pb.constraints): pb.constraints.remove(c)
def world(v): return arm.matrix_world @ v
def angle(a,b):
    if a.length<1e-7 or b.length<1e-7: return 0.0
    return math.degrees(a.angle(b))
results=[]; accepted=[]
for name in legs:
    upper=arm.pose.bones[name+'_01']; lower=arm.pose.bones[name+'_02']; foot=arm.pose.bones[name+'_03']
    hip=upper.head.copy(); knee=upper.tail.copy(); ankle=lower.tail.copy()
    plane=(knee-hip).cross(ankle-knee)
    if plane.length<1e-7: plane=Vector((1,0,0))
    plane.normalize(); pole_local=knee+plane*max((upper.length+lower.length)*1.5,0.25)
    td=bpy.data.objects.new('CMAI_IKTest_Target_'+name,None); td.empty_display_type='SPHERE'; td.empty_display_size=.025; td.location=world(ankle); scene.collection.objects.link(td)
    pd=bpy.data.objects.new('CMAI_IKTest_Pole_'+name,None); pd.empty_display_type='CUBE'; pd.empty_display_size=.02; pd.location=world(pole_local); scene.collection.objects.link(pd)
    before={{bn:(arm.pose.bones[bn].tail-arm.pose.bones[bn].head).copy() for bn in (name+'_01',name+'_02',name+'_03')}}
    c=upper.constraints.new('IK'); c.name='CMAI_IKTest_'+name; c.target=td; c.pole_target=pd; c.chain_count=2; c.influence=1.0
    bpy.context.view_layer.update()
    after={{bn:(arm.pose.bones[bn].tail-arm.pose.bones[bn].head).copy() for bn in before}}; diffs={{bn:angle(before[bn],after[bn]) for bn in before}}; maximum=max(diffs.values()); passed=maximum<=2.0
    if not passed: upper.constraints.remove(c); bpy.context.view_layer.update()
    else: accepted.append(name)
    results.append({{'leg':name,'passed':passed,'max_angle_deg':maximum,'bone_angle_deg':diffs,'pole_local':tuple(round(x,6) for x in pole_local),'chain_count':2}})
scene.render.resolution_percentage=50; scene.render.filepath=r'{Path(a.render).resolve()}'; scene.frame_set(1); bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=r'{Path(a.output).resolve()}')
print(json.dumps({{'legs':results,'accepted':accepted,'accepted_count':len(accepted),'threshold_deg':2.0}}))
"""
    r=subprocess.run([a.blender,'--background','--python-expr',expr],capture_output=True,text=True,check=True)
    data={}
    for line in reversed(r.stdout.splitlines()):
        if line.strip().startswith('{'): data=json.loads(line); break
    if not data: raise RuntimeError('No IK validation JSON: '+r.stderr[-2000:])
    data.update({'input':str(Path(a.blend).resolve()),'output':str(Path(a.output).resolve()),'render':str(Path(a.render).resolve())})
    Path(a.report).write_text(json.dumps(data,indent=2),encoding='utf-8'); print(json.dumps(data,indent=2))
if __name__=='__main__': main()
