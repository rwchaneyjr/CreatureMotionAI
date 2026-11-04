import argparse, subprocess
from pathlib import Path
def main():
 p=argparse.ArgumentParser(); p.add_argument('--blender',required=True); p.add_argument('--source',required=True); p.add_argument('--output',required=True); a=p.parse_args()
 out=str(Path(a.output).resolve()).replace('\\','/')
 expr=f'''import bpy,json,math
from mathutils import Vector
bpy.ops.wm.open_mainfile(filepath=r"{Path(a.source).resolve()}")
arm=next(o for o in bpy.data.objects if o.type=='ARMATURE'); legs=['Leg_Front.L','Leg_Front.R','Leg_MidFront.L','Leg_MidFront.R','Leg_MidRear.L','Leg_MidRear.R','Leg_Rear.L','Leg_Rear.R']
def w(pb,tail=False): return arm.matrix_world@(pb.tail if tail else pb.head)
rows=[]
for n in legs:
 hip=w(arm.pose.bones[n+'_01']); knee=w(arm.pose.bones[n+'_01'],True); ankle=w(arm.pose.bones[n+'_02'],True); foot=w(arm.pose.bones[n+'_03'],True)
 a=(knee-hip).normalized(); b=(ankle-knee).normalized(); c=(foot-ankle).normalized(); plane=a.cross(b); bend=plane.normalized() if plane.length>1e-8 else Vector((0,0,1)); angle=math.degrees(a.angle(b)); rows.append({{'leg':n,'hip':list(hip),'knee':list(knee),'ankle':list(ankle),'foot':list(foot),'bend_plane':list(bend),'bend_plane_length':plane.length,'joint_angle_deg':angle,'leg_length':(knee-hip).length+(ankle-knee).length+(foot-ankle).length,'nearly_straight':plane.length<1e-4}})
out={{'status':'bend_diagnostic_complete','source':r'{str(Path(a.source).resolve())}','legs':rows,'notes':['Per-leg bend planes measured from original evaluated resting pose.','No rig, mesh, or action was modified.']}}
open(r'{out}','w').write(json.dumps(out,indent=2)); print(json.dumps(out))'''
 subprocess.run([a.blender,'--background','--python-expr',expr],check=True)
if __name__=='__main__': main()
