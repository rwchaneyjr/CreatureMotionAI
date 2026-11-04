import argparse, subprocess
from pathlib import Path
def main():
 p=argparse.ArgumentParser(); p.add_argument('--blender',required=True); p.add_argument('--blend',required=True); p.add_argument('--report',required=True); a=p.parse_args()
 rp=str(Path(a.report).resolve()).replace('\\','/')
 expr=f'''import bpy,json,math
from mathutils import Vector
bpy.ops.wm.open_mainfile(filepath=r"{Path(a.blend).resolve()}"); s=bpy.context.scene; arm=next(o for o in bpy.data.objects if o.type=='ARMATURE'); mesh=next(o for o in bpy.data.objects if o.type=='MESH'); n='Leg_Front.L'; pb=arm.pose.bones[n+'_03']; target=bpy.data.objects.get('CMAI_FrontL_Step_Target')
def foot(): return arm.matrix_world@pb.tail
def ori(): return (arm.matrix_world.to_3x3()@pb.matrix.to_3x3()).to_euler()
s.frame_set(1); bpy.context.view_layer.update(); base=foot(); baseori=ori(); rows=[]
for f in range(1,25):
 s.frame_set(f); bpy.context.view_layer.update(); p=foot(); o=ori(); tv=target.matrix_world.translation; rows.append({{'frame':f,'foot':list(p),'target_error':(tv-p).length,'ground_penetration':max(0.0,-(p.z-base.z)),'orientation_deviation_deg':max(abs(math.degrees(o[i]-baseori[i])) for i in range(3)),'contact_slide':(p-base).length if f<=12 else None,'swing_clearance':p.z-base.z if f>12 else None}})
out={{'status':'front_leg_physical_validation','blend':r'{str(Path(a.blend).resolve())}','rows':rows,'max_ground_penetration':max(x['ground_penetration'] for x in rows),'max_orientation_deviation_deg':max(x['orientation_deviation_deg'] for x in rows),'max_target_error':max(x['target_error'] for x in rows),'max_contact_slide':max(x['contact_slide'] for x in rows if x['contact_slide'] is not None),'min_swing_clearance':min(x['swing_clearance'] for x in rows if x['swing_clearance'] is not None),'self_collision':'NOT_TESTED_BVH','mesh_foot_ground':'BONE_ENDPOINT_PROXY','overall':'BLOCKED_PENDING_BVH_AND_RENDER_REVIEW'}}
open(r'{rp}','w').write(json.dumps(out,indent=2)); print(json.dumps(out))'''
 subprocess.run([a.blender,'--background','--python-expr',expr],check=True)
if __name__=='__main__': main()
