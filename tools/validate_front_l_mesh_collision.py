"""Localized mesh-hugging Front.L-vs-body collision validation.

The original mesh and animation are read-only.  A static BVH is built from the
resting evaluated body surface; each test frame builds a small BVH for the
deformed Front.L region.  Results are conservative triangle-overlap evidence,
not a penetration-depth measurement.
"""
import argparse, json, sys, time
from pathlib import Path

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

CHAIN = ["Leg_Front.L_01", "Leg_Front.L_02", "Leg_Front.L_03"]
FRAMES = [1, 6, 12, 18, 24]

def world_mesh(obj, deps, frame):
    bpy.context.scene.frame_set(frame); bpy.context.view_layer.update()
    ev = obj.evaluated_get(deps); me = ev.to_mesh()
    mw = ev.matrix_world.copy()
    verts = [mw @ v.co for v in me.vertices]
    me.calc_loop_triangles()
    tris = [(t.index, tuple(t.vertices)) for t in me.loop_triangles]
    ev.to_mesh_clear()
    return verts, tris

def bbox(verts):
    xs=[v.x for v in verts]; ys=[v.y for v in verts]; zs=[v.z for v in verts]
    return (min(xs),min(ys),min(zs)), (max(xs),max(ys),max(zs))

def expanded_intersects(a, b, pad):
    (aminx,aminy,aminz),(amaxx,amaxy,amaxz)=a
    (bminx,bminy,bminz),(bmaxx,bmaxy,bmaxz)=b
    return not (amaxx+pad < bminx or bmaxx+pad < aminx or amaxy+pad < bminy or bmaxy+pad < aminy or amaxz+pad < bminz or bmaxz+pad < aminz)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--blend',required=True); ap.add_argument('--out',required=True)
    ap.add_argument('--pad',type=float,default=.12)
    argv=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else sys.argv[1:]
    args=ap.parse_args(argv); t0=time.perf_counter()
    bpy.ops.wm.open_mainfile(filepath=str(Path(args.blend).resolve()))
    deps=bpy.context.evaluated_depsgraph_get(); mesh=next(o for o in bpy.data.objects if o.type=='MESH' and not o.name.startswith('CMAI_'))
    vg_ids={n:mesh.vertex_groups[n].index for n in CHAIN if mesh.vertex_groups.get(n)}
    leg_ids={v.index for v in mesh.data.vertices if any(g.group in vg_ids.values() and g.weight>.05 for g in v.groups)}
    if not leg_ids: raise RuntimeError('No Front.L weighted vertices found')
    rest_v, rest_tris=world_mesh(mesh,deps,1)
    leg_pts=[rest_v[i] for i in leg_ids]; leg_box=bbox(leg_pts)
    # Body surface: triangles with no Front.L-influenced vertices, limited to a
    # conservative neighborhood around the resting leg.
    body_tris=[]; excluded=0
    for tid,vi in rest_tris:
        if any(i in leg_ids for i in vi): excluded+=1; continue
        if expanded_intersects(bbox([rest_v[i] for i in vi]),leg_box,args.pad): body_tris.append((tid,vi))
    body_ids=sorted({i for _,vi in body_tris for i in vi})
    body_index={old:i for i,old in enumerate(body_ids)}
    body_polys=[tuple(body_index[i] for i in vi) for _,vi in body_tris]
    body_coords=[rest_v[i] for i in body_ids]
    body_tree=BVHTree.FromPolygons(body_coords,body_polys,all_triangles=True)
    body_tid=[tid for tid,_ in body_tris]
    def collisions(frame):
        verts,tris=world_mesh(mesh,deps,frame)
        moving=[(tid,vi) for tid,vi in tris if any(i in leg_ids for i in vi)]
        mids=sorted({i for _,vi in moving for i in vi}); mi={old:i for i,old in enumerate(mids)}
        polys=[tuple(mi[i] for i in vi) for _,vi in moving]; coords=[verts[i] for i in mids]
        tree=BVHTree.FromPolygons(coords,polys,all_triangles=True)
        pairs=[]
        for li,bi in tree.overlap(body_tree):
            ltid,lvi=moving[li]; btid,bvi=body_tris[bi]
            if set(lvi)&set(bvi): continue
            p=(coords[polys[li][0]]+coords[polys[li][1]]+coords[polys[li][2]])/3
            q=(body_coords[body_polys[bi][0]]+body_coords[body_polys[bi][1]]+body_coords[body_polys[bi][2]])/3
            pairs.append({'leg_triangle_id':ltid,'body_triangle_id':btid,'location':[float(x) for x in (p+q)*.5],'leg_vertices':list(lvi),'body_vertices':list(bvi)})
        return pairs
    baseline=collisions(1); base_keys={(x['leg_triangle_id'],x['body_triangle_id']) for x in baseline}; rows=[]
    for f in FRAMES:
        hits=collisions(f); new=[x for x in hits if (x['leg_triangle_id'],x['body_triangle_id']) not in base_keys]
        rows.append({'frame':f,'all_overlap_count':len(hits),'baseline_overlap_count':len(baseline),'new_intersection_count':len(new),'new_intersections':new})
    result={'status':'PASS_LOCALIZED_MESH' if all(r['new_intersection_count']==0 for r in rows) else 'FAIL_NEW_MESH_INTERSECTION','blend':str(Path(args.blend).resolve()),'mesh':mesh.name,'chain':CHAIN,'tested_frames':FRAMES,'front_l_weighted_vertex_count':len(leg_ids),'body_triangle_count':len(body_tris),'excluded_leg_touch_triangles':excluded,'neighborhood_pad':args.pad,'baseline_intersections':baseline,'frames':rows,'runtime_seconds':time.perf_counter()-t0,'penetration_depth':'NOT_COMPUTED','note':'BVH overlap is triangle intersection evidence. Shared original vertices are excluded; adjacent but non-shared surface overlaps are retained.'}
    Path(args.out).write_text(json.dumps(result,indent=2),encoding='utf-8'); print(json.dumps({'status':result['status'],'body_triangles':len(body_tris),'baseline':len(baseline),'max_new':max((r['new_intersection_count'] for r in rows),default=0),'runtime_seconds':result['runtime_seconds']}))
if __name__=='__main__': main()
