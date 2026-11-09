import sys,json,bpy
from pathlib import Path
argv=sys.argv[sys.argv.index('--')+1:]; blend,report=argv[:2]
bpy.ops.wm.open_mainfile(filepath=blend); s=bpy.context.scene; arm=bpy.data.objects['CrimsonSpineBehemoth_Rig']; mesh=bpy.data.objects['CrimsonSpineBehemoth_Mesh']
legs=['Front.L','Front.R','MidFront.L','MidFront.R','MidRear.L','MidRear.R','Rear.L','Rear.R']
def p(n,end=True):
    b=arm.pose.bones[n]; return arm.matrix_world@(b.tail if end else b.head)
s.frame_set(1); bpy.context.view_layer.update(); rest={x:p('Leg_'+x+'_03') for x in legs}; base=[mesh.matrix_world@v.co for v in mesh.data.vertices]
rows=[]
for f in (1,7,13,19,24):
    s.frame_set(f); bpy.context.view_layer.update(); cur=[p('Leg_'+x+'_03') for x in legs]; disp=[(cur[i]-rest[legs[i]]).length for i in range(8)]
    ev=mesh.evaluated_get(bpy.context.evaluated_depsgraph_get()); tmp=ev.to_mesh(); pts=[mesh.matrix_world@v.co for v in tmp.vertices]; ev.to_mesh_clear(); dv=[(a-b).length for a,b in zip(pts,base)]
    rows.append({'frame':f,'foot_displacement':dict(zip(legs,[round(x,8) for x in disp])),'mesh_max_displacement':round(max(dv),8),'mesh_mean_displacement':round(sum(dv)/len(dv),8),'mesh_min_z':round(min(v.z for v in pts),8)})
s.frame_set(24); bpy.context.view_layer.update()
out={'status':'LAYERED_FK_VALIDATION','frames':rows,'loop_foot_max_delta':max((p('Leg_'+x+'_03')-rest[x]).length for x in legs),'note':'Ground and collision are not fully validated here.'}
Path(report).write_text(json.dumps(out,indent=2),encoding='utf-8'); print(json.dumps(out))
