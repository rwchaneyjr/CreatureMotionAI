import argparse, subprocess
from pathlib import Path
def main():
 p=argparse.ArgumentParser(); p.add_argument('--blender',required=True); p.add_argument('--blend',required=True); p.add_argument('--report',required=True); a=p.parse_args()
 rp=str(Path(a.report).resolve()).replace('\\','/')
 expr=f'''import bpy,json,math
from mathutils import Vector
bpy.ops.wm.open_mainfile(filepath=r"{Path(a.blend).resolve()}"); s=bpy.context.scene; arm=next(o for o in bpy.data.objects if o.type=='ARMATURE'); n='Leg_Front.L'
def w(pb,tail=False): return arm.matrix_world@(pb.tail if tail else pb.head)
def state():
 hip=w(arm.pose.bones[n+'_01']); knee=w(arm.pose.bones[n+'_01'],True); foot=w(arm.pose.bones[n+'_03'],True); t=bpy.data.objects.get('CMAI_FrontL_Step_Target'); return hip,knee,foot,t
s.frame_set(1); bpy.context.view_layer.update(); h0,k0,f0,t0=state(); axis0=(f0-h0).normalized(); rel0=k0-h0; side0=rel0-axis0*rel0.dot(axis0); straight=side0.length<1e-6; ref=side0.normalized() if not straight else Vector((0,0,1)); rows=[]
for f in range(1,25):
 s.frame_set(f); bpy.context.view_layer.update(); h,k,foot,t=state(); axis=(foot-h); L=axis.length; axis.normalize() if L>1e-8 else None; rel=k-h; side=rel-axis*rel.dot(axis) if L>1e-8 else Vector(); align=side.dot(ref); side_len=side.length; err=(t.matrix_world.translation-foot).length
 rows.append({{'frame':f,'target_error':err,'knee_side_signed':align,'knee_side_magnitude':side_len,'same_bend_side':True if straight or align>=-1e-6 else False,'near_straight':side_len<1e-5}})
out={{'status':'valid_knee_side_reassessment','blend':r'{str(Path(a.blend).resolve())}','reference_side_length':side0.length,'rows':rows,'max_target_error':max(x['target_error'] for x in rows),'first_target_error_over_0.01':next((x['frame'] for x in rows if x['target_error']>0.01),None),'first_knee_side_flip':next((x['frame'] for x in rows if not x['same_bend_side']),None),'note':'Signed knee offset is measured perpendicular to the current hip-foot axis and compared with the original resting knee-side vector.'}}
open(r'{rp}','w').write(json.dumps(out,indent=2)); print(json.dumps(out))'''
 subprocess.run([a.blender,'--background','--python-expr',expr],check=True)
if __name__=='__main__': main()
