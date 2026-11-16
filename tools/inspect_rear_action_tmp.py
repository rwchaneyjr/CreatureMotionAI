import bpy, sys, json
from pathlib import Path
blend=sys.argv[-2]; out=Path(sys.argv[-1])
bpy.ops.wm.open_mainfile(filepath=str(Path(blend).resolve()))
s=bpy.context.scene; a=next(o for o in s.objects if o.type=='ARMATURE')
act=a.animation_data.action if a.animation_data else None
rows=[]
for f in (1,30,41,70,110):
 s.frame_set(f); bpy.context.view_layer.update()
 row={'frame':f,'action':act.name if act else None,'bones':{}}
 for n in ['Leg_Rear.L_01','Leg_Rear.L_02','Leg_Rear.L_03','Leg_Rear.R_01','Leg_Rear.R_02','Leg_Rear.R_03']:
  p=a.pose.bones[n]; row['bones'][n]={'head':[float(x) for x in a.matrix_world@p.head],'tail':[float(x) for x in a.matrix_world@p.tail],'basis':[[float(x) for x in r] for r in p.matrix_basis]}
 rows.append(row)
out.write_text(json.dumps(rows,indent=2))
print(json.dumps({'action':act.name if act else None,'frames':rows},separators=(',',':')))
