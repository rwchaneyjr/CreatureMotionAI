import sys,json,bpy
from pathlib import Path
argv=sys.argv[sys.argv.index('--')+1:]; blend,report=argv[:2]
bpy.ops.wm.open_mainfile(filepath=blend); s=bpy.context.scene; arm=bpy.data.objects['CrimsonSpineBehemoth_Rig']; mesh=bpy.data.objects['CrimsonSpineBehemoth_Mesh']
legs=['Front.L','Front.R','MidFront.L','MidFront.R','MidRear.L','MidRear.R','Rear.L','Rear.R']
groups={x:{g.index for g in mesh.vertex_groups if g.name in {'Leg_'+x+'_01','Leg_'+x+'_02','Leg_'+x+'_03'}} for x in legs}
def foot(): return {x:arm.matrix_world@arm.pose.bones['Leg_'+x+'_03'].tail for x in legs}
def eval_points():
    ev=mesh.evaluated_get(bpy.context.evaluated_depsgraph_get()); tmp=ev.to_mesh(); pts=[mesh.matrix_world@v.co for v in tmp.vertices]; ev.to_mesh_clear(); return pts
def indices(x): return [v.index for v in mesh.data.vertices if any(w.group in groups[x] and w.weight>.05 for w in v.groups)]
s.frame_set(1); bpy.context.view_layer.update(); basepts=eval_points(); ground=min(p.z for p in basepts); restfeet=foot(); footidx={x:indices(x) for x in legs}; rows=[]; maxpen=0; maxfloat=0
for f in range(1,25):
    s.frame_set(f); bpy.context.view_layer.update(); pts=eval_points(); fs=foot(); low={}; pen={}; slide={}
    for x in legs:
        vals=[pts[i].z for i in footidx[x] if i<len(pts)]; z=min(vals) if vals else None; low[x]=z; pen[x]=max(0.0,ground-z) if z is not None else None
        slide[x]=(fs[x]-restfeet[x]).length
        if pen[x] is not None: maxpen=max(maxpen,pen[x])
        if z is not None: maxfloat=max(maxfloat,max(0.0,z-ground))
    rows.append({'frame':f,'lowest_z':low,'penetration':pen,'foot_displacement_from_rest':slide})
s.frame_set(1); bpy.context.view_layer.update()
out={'status':'POLISH_VALIDATION','ground_reference_z':ground,'frames':rows,'max_ground_penetration':maxpen,'max_foot_height_above_rest_ground':maxfloat,'collision_status':'UNVERIFIED','collision_note':'No proxy collection was present in this working file; no collision result is claimed.','loop_check':'Frame 1 and frame 25 are explicit rest keys; frame 24 is evaluated separately.'}
Path(report).write_text(json.dumps(out,indent=2),encoding='utf-8'); print(json.dumps({'report':report,'max_penetration':maxpen,'max_float':maxfloat}))
