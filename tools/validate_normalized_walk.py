import argparse, subprocess, json
from pathlib import Path
def main():
 p=argparse.ArgumentParser(); p.add_argument('--blender',required=True); p.add_argument('--blend',required=True); p.add_argument('--report',required=True); a=p.parse_args()
 rp=str(Path(a.report).resolve()).replace('\\','/')
 expr=f'''import bpy,json
from mathutils import Vector
s=bpy.context.scene; arm=next(o for o in bpy.data.objects if o.type=='ARMATURE'); legs=['Leg_Front.L','Leg_Front.R','Leg_MidFront.L','Leg_MidFront.R','Leg_MidRear.L','Leg_MidRear.R','Leg_Rear.L','Leg_Rear.R']
def foot(n): return arm.matrix_world@arm.pose.bones[n+'_03'].tail
s.frame_set(1); bpy.context.view_layer.update(); base={{n:foot(n) for n in legs}}; root0=arm.matrix_world.translation.copy(); rows=[]
for f in (1,6,12,18,24):
 s.frame_set(f); bpy.context.view_layer.update(); root=arm.matrix_world.translation.copy(); row={{'frame':f,'root':list(root),'root_displacement':(root-root0).length,'feet':{{}}}}
 for n in legs:
  t=bpy.data.objects.get('CMAI_Normalized_Target_'+n); q=t.matrix_world.translation; p=foot(n); row['feet'][n]={{'target_error':(q-p).length,'disp':(p-base[n]).length,'lift':p.z-base[n].z}}
 rows.append(row)
out={{'status':'normalized_walk_validation_complete','frames':rows,'checks':{{'root_travel':rows[-1]['root_displacement']>0.02,'feet_move':max(v['disp'] for r in rows for v in r['feet'].values())>0.05,'ik_target_error':max(v['target_error'] for r in rows for v in r['feet'].values())<0.02,'mesh_collision':'NOT_TESTED','ground_contact':'NOT_TESTED','render':'NOT_CREATED'}}}}
open(r'{rp}','w').write(json.dumps(out,indent=2)); print(json.dumps(out))'''
 subprocess.run([a.blender,'--background',a.blend,'--python-expr',expr],check=True)
if __name__=='__main__': main()
