import bpy,sys,json,math
from pathlib import Path
blend=Path(sys.argv[-2]); out=Path(sys.argv[-1]); bpy.ops.wm.open_mainfile(filepath=str(blend.resolve()))
s=bpy.context.scene; a=next(o for o in s.objects if o.type=='ARMATURE'); names=['Leg_Front.L_01','Leg_Front.L_02','Leg_Front.L_03']; rows=[]
for f in range(1,121):
 s.frame_set(f); bpy.context.view_layer.update(); p=[a.matrix_world@a.pose.bones[n].head for n in names]+[a.matrix_world@a.pose.bones[names[-1]].tail]
 knee=math.degrees((p[0]-p[1]).angle(p[2]-p[1])); rows.append({'frame':f,'foot':[float(x) for x in p[3]],'knee_angle_deg':knee})
result={'fps':24,'cycle_frames':120,'leg':'Front.L','events':{'foot_forward':max(rows,key=lambda r:r['foot'][1]),'foot_backward':min(rows,key=lambda r:r['foot'][1]),'foot_highest':max(rows,key=lambda r:r['foot'][2]),'foot_lowest':min(rows,key=lambda r:r['foot'][2]),'knee_max_bend':min(rows,key=lambda r:r['knee_angle_deg']),'knee_min_bend':max(rows,key=lambda r:r['knee_angle_deg'])},'rows':rows}
out.write_text(json.dumps(result,indent=2)); print(json.dumps(result['events'],separators=(',',':')))
