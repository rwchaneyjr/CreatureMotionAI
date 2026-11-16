import bpy,sys,json
from pathlib import Path
src=sys.argv[-2]; out=Path(sys.argv[-1]); out.parent.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=src); s=bpy.context.scene; a=next(o for o in s.objects if o.type=='ARMATURE')
legs={k:[f'Leg_{k}_{i:02d}' for i in (1,2,3)] for k in ('Rear.R','Rear.L','MidRear.R','MidRear.L')}
rows=[]
for f in range(1,122):
    s.frame_set(f); bpy.context.view_layer.update(); r={'frame':f,'legs':{}}
    for leg,names in legs.items():
        p=[a.pose.bones[n] for n in names]; pts=[a.matrix_world@p[0].head,a.matrix_world@p[0].tail,a.matrix_world@p[1].tail,a.matrix_world@p[2].tail]
        r['legs'][leg]={'basis':{n:[list(x) for x in a.pose.bones[n].matrix_basis] for n in names},'points':[list(x) for x in pts], 'bend_normal':list(((pts[1]-pts[0]).cross(pts[2]-pts[1])).normalized())}
    rows.append(r)
out.write_text(json.dumps({'source':src,'frame_range':[1,121],'fps':24,'legs':list(legs),'frames':rows},indent=2),encoding='utf-8'); print(str(out))
