import argparse, subprocess
from pathlib import Path
def main():
 p=argparse.ArgumentParser(); p.add_argument('--blender',required=True); p.add_argument('--blend',required=True); p.add_argument('--report',required=True); a=p.parse_args(); rp=str(Path(a.report).resolve()).replace('\\','/')
 expr=f'''import bpy,json
bpy.ops.wm.open_mainfile(filepath=r"{Path(a.blend).resolve()}"); s=bpy.context.scene; arm=next(o for o in bpy.data.objects if o.type=='ARMATURE'); names=['Leg_Front.L_01','Leg_Front.L_02','Leg_Front.L_03']; rows=[]
for f in (1,12,13,24):
 s.frame_set(f); bpy.context.view_layer.update(); r={{'frame':f,'bones':{{}}}}
 for n in names:
  pb=arm.pose.bones[n]; q=(arm.matrix_world.to_quaternion()@pb.matrix.to_quaternion()).normalized(); r['bones'][n]={{'quat':list(q),'head':list(arm.matrix_world@pb.head),'tail':list(arm.matrix_world@pb.tail)}}
 t=bpy.data.objects.get('CMAI_FrontL_Step_Target'); p=bpy.data.objects.get('CMAI_FrontL_Step_Pole'); r['target']=list(t.matrix_world.translation); r['pole']=list(p.matrix_world.translation); rows.append(r)
open(r'{rp}','w').write(json.dumps({{'status':'orientation_diagnostic_complete','rows':rows,'note':'World-space pose quaternions recorded; q and -q are equivalent.'}},indent=2)); print(json.dumps({{'status':'orientation_diagnostic_complete','report':r'{rp}'}}))'''
 subprocess.run([a.blender,'--background','--python-expr',expr],check=True)
if __name__=='__main__': main()
