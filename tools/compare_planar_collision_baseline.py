"""Compare reduced-BVH collision pairs in the original pose and Rear.L action."""
import argparse, json, sys, time
from pathlib import Path

def run_file(bpy, path, frames, ratio):
    from mathutils.bvhtree import BVHTree
    bpy.ops.wm.open_mainfile(filepath=str(Path(path).resolve()))
    scene=bpy.context.scene; mesh=next(o for o in scene.objects if o.type=='MESH')
    out={}
    for f in frames:
        scene.frame_set(f); bpy.context.view_layer.update(); deps=bpy.context.evaluated_depsgraph_get()
        ev=mesh.evaluated_get(deps); data=ev.to_mesh(); data.calc_loop_triangles()
        proxy=bpy.data.objects.new('CMAI_tmp_proxy',data.copy()); scene.collection.objects.link(proxy); mod=proxy.modifiers.new('CMAI_tmp_decimate','DECIMATE'); mod.ratio=ratio; deps.update()
        pev=proxy.evaluated_get(deps); pd=pev.to_mesh(); pd.calc_loop_triangles(); verts=[proxy.matrix_world@v.co for v in pd.vertices]; tris=[tuple(t.vertices) for t in pd.loop_triangles]; tree=BVHTree.FromPolygons(verts,tris,all_triangles=True)
        pairs=set()
        for a,b in tree.overlap(tree):
            if a>=b or set(tris[a]).intersection(tris[b]): continue
            pairs.add((min(a,b),max(a,b)))
        out[str(f)]={'pairs':sorted([list(x) for x in pairs]),'count':len(pairs)}
        pev.to_mesh_clear(); ev.to_mesh_clear(); bpy.data.objects.remove(proxy,do_unlink=True)
    return out

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--original',required=True); ap.add_argument('--animated',required=True); ap.add_argument('--report',required=True); ap.add_argument('--ratio',type=float,default=.08)
    argv=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else sys.argv[1:]; a=ap.parse_args(argv)
    import bpy
    frames=list(range(1,25)); base=run_file(bpy,a.original,[1],a.ratio); anim=run_file(bpy,a.animated,frames,a.ratio); b=set(map(tuple,base['1']['pairs'])); rows=[]
    for k,v in anim.items():
        s=set(map(tuple,v['pairs'])); new=s-b; rows.append({'frame':int(k),'baseline_pair_count':len(b),'animated_pair_count':len(s),'new_vs_rest_pair_count':len(new),'new_pairs':[list(x) for x in sorted(new)][:100],'classification':'NO_NEW_REDUCED_PROXY_PAIRS' if not new else 'NEW_OR_WORSENED_REDUCED_PROXY_PAIRS'})
    result={'status':'BASELINE_RELATIVE','original_resting_frame':1,'frames':rows,'proxy_ratio':a.ratio,'note':'Pairs are reduced-BVH triangle identifiers; this establishes baseline-relative evidence, not reliable physical penetration depth or anatomical identity.'}
    Path(a.report).write_text(json.dumps(result,indent=2),encoding='utf-8'); print(json.dumps({'frames':len(rows),'new_frames':sum(r['new_vs_rest_pair_count']>0 for r in rows)}))
if __name__=='__main__': main()
