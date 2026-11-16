import json, sys
from pathlib import Path
import bpy
from mathutils.bvhtree import BVHTree

BLEND = sys.argv[-2]
OUT = Path(sys.argv[-1])
OUT.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=BLEND)
PAIRS = [
    (['Leg_Rear.L_01','Leg_Rear.L_02','Leg_Rear.L_03'], ['Leg_MidRear.L_01','Leg_MidRear.L_02','Leg_MidRear.L_03']),
    (['Leg_Rear.R_01','Leg_Rear.R_02','Leg_Rear.R_03'], ['Leg_MidRear.R_01','Leg_MidRear.R_02','Leg_MidRear.R_03']),
]

scene=bpy.context.scene
mesh=next(o for o in scene.objects if o.type=='MESH')
arm=next(o for o in scene.objects if o.type=='ARMATURE')
mesh.data.calc_loop_triangles()

def groups(names):
    return {mesh.vertex_groups[n].index for n in names if mesh.vertex_groups.get(n)}
def select(names):
    gs=groups(names); out=set()
    for v in mesh.data.vertices:
        w=sum(g.weight for g in v.groups if g.group in gs)
        mx=max((g.weight for g in v.groups), default=0.0)
        if w >= .35 and w >= mx*.75: out.add(v.index)
    return out
def tri_subset(data, allowed):
    return [tuple(t.vertices) for t in data.loop_triangles if len(set(t.vertices)&allowed)>=2]

frames=[]; total=0
test_frames=[30,70,110]
for frame in test_frames:
    scene.frame_set(frame); bpy.context.view_layer.update(); deps=bpy.context.evaluated_depsgraph_get()
    ev=mesh.evaluated_get(deps); data=ev.to_mesh(); data.calc_loop_triangles()
    verts=[ev.matrix_world@v.co for v in data.vertices]
    pair_rows=[]
    for a_names,b_names in PAIRS:
        ia=select(a_names); ib=select(b_names)
        ta=tri_subset(data,ia); tb=tri_subset(data,ib)
        if not ta or not tb: continue
        oa=BVHTree.FromPolygons(verts,ta,all_triangles=True); ob=BVHTree.FromPolygons(verts,tb,all_triangles=True)
        raw=oa.overlap(ob); filt=[]
        for x,y in raw:
            if set(ta[x]).intersection(tb[y]): continue
            filt.append((x,y))
        if filt:
            pair_rows.append({'a':a_names,'b':b_names,'raw':len(raw),'filtered':len(filt)})
            total+=len(filt)
    frames.append({'frame':frame,'pairs':pair_rows})
    ev.to_mesh_clear()
result={'blend':BLEND,'frames':frames,'filtered_surface_overlap_samples':total,
        'status':'ACTUAL_MESH_INTERSECTION' if total else 'NO_ACTUAL_MESH_INTERSECTION',
        'method':'evaluated weighted mesh BVH; shared source-vertex triangles excluded',
        'pairs_tested':PAIRS}
(OUT/'current_surface_collision_report.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps({'status':result['status'],'samples':total,'frames':sum(bool(x['pairs']) for x in frames)}))
