"""Baseline-relative collision check using identical source triangle topology."""
import argparse, json, sys
from pathlib import Path

def collect(bpy, path, frames):
    from mathutils.bvhtree import BVHTree
    bpy.ops.wm.open_mainfile(filepath=str(Path(path).resolve()))
    scene=bpy.context.scene; mesh=next(o for o in scene.objects if o.type=='MESH')
    deps=scene.view_layers[0].depsgraph if hasattr(scene.view_layers[0],'depsgraph') else bpy.context.evaluated_depsgraph_get()
    source_tris=[tuple(t.vertices) for t in mesh.data.loop_triangles] if mesh.data.loop_triangles else []
    mesh.data.calc_loop_triangles(); source_tris=[tuple(t.vertices) for t in mesh.data.loop_triangles]
    adjacent=set()
    for i,a in enumerate(source_tris):
        sa=set(a)
        for j in range(i+1,len(source_tris)):
            if sa.intersection(source_tris[j]): adjacent.add((i,j))
    result={}
    for f in frames:
        scene.frame_set(f); bpy.context.view_layer.update(); deps=bpy.context.evaluated_depsgraph_get(); ev=mesh.evaluated_get(deps); data=ev.to_mesh(); data.calc_loop_triangles()
        tris=[tuple(t.vertices) for t in data.loop_triangles]
        if len(tris)!=len(source_tris): raise RuntimeError(f'topology changed at frame {f}: {len(source_tris)} vs {len(tris)} triangles')
        verts=[ev.matrix_world@v.co for v in data.vertices]; tree=BVHTree.FromPolygons(verts,tris,all_triangles=True); pairs=[]
        for a,b in tree.overlap(tree):
            if a>=b or (a,b) in adjacent: continue
            pairs.append((a,b))
        result[str(f)]={'pairs':sorted(set(pairs)),'count':len(set(pairs))}; ev.to_mesh_clear()
    return result

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--original',required=True); ap.add_argument('--animated',required=True); ap.add_argument('--report',required=True)
    argv=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else sys.argv[1:]; a=ap.parse_args(argv)
    import bpy
    base=collect(bpy,a.original,[1]); anim=collect(bpy,a.animated,list(range(1,25))); b=set(map(tuple,base['1']['pairs'])); rows=[]
    for k,v in anim.items():
        s=set(map(tuple,v['pairs'])); rows.append({'frame':int(k),'rest_pair_count':len(b),'animated_pair_count':len(s),'new_pair_count':len(s-b),'resolved_pair_count':len(b-s),'new_pairs':[list(x) for x in sorted(s-b)][:100]})
    result={'status':'BASELINE_RELATIVE','same_source_topology':True,'adjacent_shared-vertex_pairs_excluded':True,'resting_pose':base['1'],'frames':rows,'note':'BVH overlap is a conservative intersection signal; triangle regions still require anatomical interpretation.'}
    Path(a.report).write_text(json.dumps(result,indent=2),encoding='utf-8'); print(json.dumps({'rest_pairs':len(b),'max_new_pairs':max(r['new_pair_count'] for r in rows)}))
if __name__=='__main__': main()
