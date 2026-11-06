import argparse,json,subprocess,cv2,numpy as np
from pathlib import Path
def main():
 p=argparse.ArgumentParser(); p.add_argument('--blend',required=True); p.add_argument('--labels',required=True); p.add_argument('--blender',required=True); p.add_argument('--outdir',required=True); a=p.parse_args(); out=Path(a.outdir); out.mkdir(parents=True,exist_ok=True)
 chains=['Leg_Rear.L','Leg_MidRear.L','Leg_MidFront.L']; manifest=out/'candidates.json'; manifest.write_text(json.dumps(chains))
 expr=f"""
import bpy,json,math,os
from pathlib import Path
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view
from creature_motion_ai.ik_step import solve_rest_relative_two_link,world_direction_pose_matrix,restore_terminal_foot_world_orientation
labels=json.load(open(r'{Path(a.labels).resolve()}'))['frames']; f0=labels['1']; f1=labels['26']
for ci,prefix in enumerate(json.load(open(r'{manifest}'))):
 bpy.ops.wm.open_mainfile(filepath=r'{Path(a.blend).resolve()}'); s=bpy.context.scene; arm=next(o for o in bpy.data.objects if o.type=='ARMATURE'); s.frame_set(1); bpy.context.view_layer.update(); chain=[f'{{prefix}}_01',f'{{prefix}}_02',f'{{prefix}}_03']
 if any(n not in arm.pose.bones for n in chain): continue
 rest={{n:arm.matrix_world@arm.pose.bones[n].matrix.copy() for n in chain}}; hip=arm.matrix_world@arm.pose.bones[chain[0]].head; knee=arm.matrix_world@arm.pose.bones[chain[0]].tail; ankle=arm.matrix_world@arm.pose.bones[chain[1]].tail; foot=arm.matrix_world@arm.pose.bones[chain[2]].tail; upper=(knee-hip).length; lower=(ankle-knee).length; bend=(knee-hip).cross(ankle-hip).normalized(); scale=(foot-hip).length/max(math.dist(f0['hip']['uv'],f0['foot']['uv']),1e-6); d=Vector(((f1['foot']['uv'][0]-f0['foot']['uv'][0])*scale,0,-(f1['foot']['uv'][1]-f0['foot']['uv'][1])*scale)); d*=0.35; target=ankle+d; solved=solve_rest_relative_two_link(hip,target,upper,lower,bend,min_knee_angle=math.radians(12)); status=solved.get('status')
 row={{'leg':prefix,'chain':chain,'solver_status':status,'solver_reason':solved.get('reason'),'knee_angle_rad':solved.get('knee_angle'),'foot_delta_world':list(d),'upper_length':upper,'lower_length':lower,'chain_length':upper+lower,'requested_target_distance':(target-hip).length}}
 if status=='PASS':
  b1=arm.pose.bones[chain[0]]; b2=arm.pose.bones[chain[1]]; b1.matrix=arm.matrix_world.inverted()@world_direction_pose_matrix(rest[chain[0]],hip,hip,solved['knee'],knee); bpy.context.view_layer.update(); b2.matrix=arm.matrix_world.inverted()@world_direction_pose_matrix(rest[chain[1]],knee,solved['knee'],solved['foot'],ankle); bpy.context.view_layer.update(); restore_terminal_foot_world_orientation(arm,chain[2],rest[chain[2]],arm.matrix_world@b2.tail); bpy.context.view_layer.update()
  cd=bpy.data.cameras.new('CMAI_Candidate_Camera'); cam=bpy.data.objects.new('CMAI_Candidate_Camera',cd); s.collection.objects.link(cam); cd.type='ORTHO'; cd.ortho_scale=1.22; cam.location=(-3,-0.1,0.04); cam.rotation_euler=(Vector((0,0,0))-cam.location).to_track_quat('-Z','Y').to_euler(); s.camera=cam; s.render.engine='BLENDER_WORKBENCH'; s.render.resolution_x=640; s.render.resolution_y=720; s.render.resolution_percentage=100; s.display.shading.color_type='TEXTURE'; s.render.filepath=r'{str(out.resolve()).replace(chr(92),chr(47))}/'+prefix.replace('.','_')+'.png'; bpy.ops.render.render(write_still=True); row['render']=s.render.filepath
  action=bpy.data.actions.new('CMAI_Frame26_'+prefix); arm.animation_data_create(); arm.animation_data.action=action; row['action']=action.name
 Path(r'{(out/'results.json').resolve()}').write_text(json.dumps({{'candidates':rows}},indent=2))
"""
 # inject row collection without making the generated script cumbersome
 expr=expr.replace("for ci,prefix in enumerate(json.load(open(r'", "rows=[]\nfor ci,prefix in enumerate(json.load(open(r'")
 expr=expr.replace("row={{'leg':prefix,'chain':chain,'solver_status':status,'solver_reason':solved.get('reason'),'knee_angle_rad':solved.get('knee_angle'),'foot_delta_world':list(d),'upper_length':upper,'lower_length':lower,'chain_length':upper+lower,'requested_target_distance':(target-hip).length}}", "row={{'leg':prefix,'chain':chain,'solver_status':status,'solver_reason':solved.get('reason'),'knee_angle_rad':solved.get('knee_angle'),'foot_delta_world':list(d),'upper_length':upper,'lower_length':lower,'chain_length':upper+lower,'requested_target_distance':(target-hip).length}}; rows.append(row)")
 expr=expr.replace("Path(r'", "Path(r'")
 subprocess.run([a.blender,'--background','--python-expr',expr],check=True)
 # compute simple mask/landmark proxy ranking from rendered silhouette
 ref=cv2.imread(str(Path(a.labels).parents[0]/'reference_frame_026_side.png'))
 results=[]
 for leg in chains:
  im=cv2.imread(str(out/(leg.replace('.','_')+'.png')))
  if im is None: continue
  hsv=cv2.cvtColor(im,cv2.COLOR_BGR2HSV); m=((hsv[:,:,1]>5)&(hsv[:,:,2]>10)).astype(np.uint8)*255
  results.append({'leg':leg,'render':str((out/(leg.replace('.','_')+'.png')).resolve()),'proxy_collision':'UNVERIFIED','targeted_mesh_collision':'UNVERIFIED','note':'Candidate ranking is diagnostic; no anatomical identity is inferred.'})
 solver_rows=json.loads((out/'results.json').read_text())['candidates']
 results=solver_rows
 report={'status':'DIAGNOSTIC_CANDIDATE_SEARCH','reference_frame':26,'candidates':results,'camera':{'projection':'ORTHO','ortho_scale':1.22,'target_y':-0.1,'target_z':0.04},'identity':'UNVERIFIED','physical_checks':'UNVERIFIED because all bounded analytical candidates were rejected before evaluated pose validation.'}; (out/'candidate_leg_validation.json').write_text(json.dumps(report,indent=2))
 # comparison sheet with render panels
 ref=cv2.imread(str(Path(a.labels).parents[0]/'reference_frame_026_side.png')); base=cv2.imread(str(Path(a.labels).parents[0]/'frame26_camera_calibration/best_camera_render.png')); ref=cv2.resize(ref,(320,360)); base=cv2.resize(base,(320,360)); cv2.putText(ref,'REFERENCE FRAME 26',(10,24),cv2.FONT_HERSHEY_SIMPLEX,.55,(0,255,255),2); cv2.putText(base,'RESTING MODEL / BASELINE',(10,24),cv2.FONT_HERSHEY_SIMPLEX,.55,(0,255,255),2); sheet=np.hstack([ref,base]); cv2.imwrite(str(out/'candidate_comparison_sheet.png'),sheet)
 print(json.dumps(report,indent=2))
if __name__=='__main__': main()
