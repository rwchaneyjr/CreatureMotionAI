import argparse, json
from pathlib import Path

def collect(bpy, path, frames):
    from mathutils.bvhtree import BVHTree
    bpy.ops.wm.open_mainfile(filepath=str(Path(path).resolve()))
    scene=bpy.context.scene; mesh=next(o for o in scene.objects if o.type=='MESH')
    mesh.data.calc_loop_triangles(); source_tris=[tuple(t.vertices) for t in mesh.data.loop_triangles]
    adjacent=set()
    for i,a in enumerate(source_tris):
        sa=set(a)
        for j in range(i+1,len(source_tris)):
            if sa.intersection(source_tris[j]): adjacent.add((i,j))
    result={}
    for f in frames:
        scene.frame_set(f); bpy.context.view_layer.update(); deps=bpy.context.evaluated_depsgraph_get(); ev=mesh.evaluated_get(deps); data=ev.to_mesh(); data.calc_loop_triangles()
        tris=[tuple(t.vertices) for t in data.loop_triangles]; verts=[ev.matrix_world@v.co for v in data.vertices]
        tree=BVHTree.FromPolygons(verts,tris,all_triangles=True); pairs=[]
        for a,b in tree.overlap(tree):
            if a>=b or (a,b) in adjacent: continue
            pairs.append((a,b))
        result[f]={'pairs':sorted(set(pairs)),'count':len(set(pairs))}; ev.to_mesh_clear()
    return result

def main():
    import bpy
    ap=argparse.ArgumentParser(); ap.add_argument('--original',required=True); ap.add_argument('--animated',required=True); ap.add_argument('--report',required=True)
    argv=__import__('sys').argv; a=ap.parse_args(argv[argv.index('--')+1:] if '--' in argv else argv[1:])
    base=collect(bpy,a.original,[1]); anim=collect(bpy,a.animated,list(range(1,121))); baseline=set(map(tuple,base['1']['pairs'])); rows=[]
    for f,v in anim.items():
        pairs=set(map(tuple,v['pairs'])); new=pairs-baseline
        rows.append({'frame':int(f),'baseline_pair_count':len(baseline),'pair_count':len(pairs),'new_pair_count':len(new),'new_pairs':[list(x) for x in sorted(new)[:100]]})
    out={'status':'PASS_NO_NEW_TRIANGLE_OVERLAPS' if not any(r['new_pair_count'] for r in rows) else 'FAIL_NEW_TRIANGLE_OVERLAPS','frames_checked':120,'max_new_pair_count':max(r['new_pair_count'] for r in rows),'rows':rows,'note':'Shared-vertex triangle pairs are excluded; remaining overlaps are conservative mesh-intersection candidates and require region interpretation.'}
    Path(a.report).write_text(json.dumps(out,indent=2),encoding='utf-8'); print(json.dumps({'status':out['status'],'max_new_pair_count':out['max_new_pair_count']}))
if __name__=='__main__': main()
