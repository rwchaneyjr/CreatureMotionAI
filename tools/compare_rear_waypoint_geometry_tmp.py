import bpy,sys,json
from pathlib import Path
from mathutils import Vector
BEFORE=sys.argv[-3]; AFTER=sys.argv[-2]; OUT=Path(sys.argv[-1]); OUT.parent.mkdir(parents=True,exist_ok=True)
legs={'Rear.R':['Leg_Rear.R_01','Leg_Rear.R_02','Leg_Rear.R_03'],'Rear.L':['Leg_Rear.L_01','Leg_Rear.L_02','Leg_Rear.L_03']}
def read(path):
 bpy.ops.wm.open_mainfile(filepath=path); s=bpy.context.scene; a=next(o for o in s.objects if o.type=='ARMATURE'); rows={}
 for f in (23,25,30,31,35,63,65,70,71,75):
  s.frame_set(f); bpy.context.view_layer.update(); rows[f]={}
  for leg,names in legs.items():
   p=[a.pose.bones[n] for n in names]; pts=[a.matrix_world@p[0].head,a.matrix_world@p[0].tail,a.matrix_world@p[1].tail,a.matrix_world@p[2].tail]
   bend=(pts[1]-pts[0]).cross(pts[2]-pts[1]); rows[f][leg]={'points':[list(x) for x in pts],'bend_normal':list(bend.normalized()) if bend.length else None}
 return rows
result={'earlier':read(BEFORE),'e2e':read(AFTER)}; OUT.write_text(json.dumps(result,indent=2),encoding='utf-8'); print(json.dumps({'output':str(OUT)}))
