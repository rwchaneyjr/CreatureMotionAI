import argparse, json, subprocess
from pathlib import Path

def main():
    p=argparse.ArgumentParser(); p.add_argument('--blender',required=True); p.add_argument('--report',required=True); a=p.parse_args()
    report_path=str(Path(a.report).resolve()).replace('\\','/')
    expr=f'''import bpy, json
from mathutils import Vector
s=bpy.context.scene; arm=next(o for o in bpy.data.objects if o.type=='ARMATURE'); mesh=next(o for o in bpy.data.objects if o.type=='MESH')
legs=['Leg_Front.L','Leg_Front.R','Leg_MidFront.L','Leg_MidFront.R','Leg_MidRear.L','Leg_MidRear.R','Leg_Rear.L','Leg_Rear.R']
def wp(pb,tail=False): return arm.matrix_world @ (pb.tail if tail else pb.head)
lengths={{n:sum(arm.data.bones[n+'_0%d'%i].length for i in (1,2,3))*arm.scale.length/3.0 for n in legs}}
body_len=(arm.matrix_world@arm.data.bones['Body_03'].tail-arm.matrix_world@arm.data.bones['Body_01'].head).length
base={{n:wp(arm.pose.bones[n+'_03'],True) for n in legs}}; targets={{n:bpy.data.objects.get('CMAI_Walk_Target_'+n) for n in legs}}
rows=[]; root0=arm.matrix_world.translation.copy()
for f in (1,6,12,18,24):
 s.frame_set(f); bpy.context.view_layer.update(); root=arm.matrix_world.translation.copy(); row={{'frame':f,'root':list(root),'root_displacement':(root-root0).length,'feet':{{}}}}
 for n in legs:
  tv=targets[n].matrix_world.translation.copy(); foot=wp(arm.pose.bones[n+'_03'],True)
  row['feet'][n]={{'target':list(tv),'foot':list(foot),'target_to_foot':(tv-foot).length,'disp_from_rest':(foot-base[n]).length,'lift':foot.z-base[n].z}}
 rows.append(row)
report={{'status':'measured_existing_test','mesh_scale':list(mesh.scale),'armature_scale':list(arm.scale),'target_scales':{{n:list(targets[n].scale) for n in legs}},'body_length_world':body_len,'leg_lengths_world':lengths,'frames':rows,'root_causes':['Previous stride/lift values were fixed .055/.045 Blender units instead of leg-relative values.','Root/body translation is absent in the existing in-place test.','Existing scene has no collider or self-collision validation.'],'code_locations':['tools/create_clean_procedural_walk.py: fixed stride=.055 and lift=.045; no root translation']}}
open(r'{report_path}','w').write(json.dumps(report,indent=2)); print(json.dumps(report))'''
    r=subprocess.run([a.blender,'--background','data/generated/clean_procedural_walk_24f.blend','--python-expr',expr],capture_output=True,text=True,check=True)
    print(r.stdout[-8000:])
if __name__=='__main__': main()
