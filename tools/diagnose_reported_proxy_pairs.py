"""Targeted mesh check for the small set of reported proxy pairs."""
import argparse, json, sys
from pathlib import Path
def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--blend',required=True); ap.add_argument('--report',required=True)
 argv=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else sys.argv[1:]; a=ap.parse_args(argv)
 import bpy
 from mathutils.bvhtree import BVHTree
 bpy.ops.wm.open_mainfile(filepath=str(Path(a.blend).resolve())); s=bpy.context.scene; m=next(o for o in s.objects if o.type=='MESH'); m.data.calc_loop_triangles(); tris=[tuple(t.vertices) for t in m.data.loop_triangles]
 pairs=[(2,'MidFront.R','MidRear.R'),(3,'MidFront.L','MidFront.L'),(4,'MidFront.L','MidFront.L'),(4,'MidFront.R','MidRear.R')]
 def ids(region):
  names=[f'Leg_{region}_{i:02d}' for i in (1,2,3)]; gi={m.vertex_groups[n].index for n in names if m.vertex_groups.get(n)}
  return {v.index for v in m.data.vertices if any(g.group in gi and g.weight>.05 for g in v.groups)}
 regions={r:ids(r) for _,r,_ in pairs}|{r:ids(r) for _,_,r in pairs}; rows=[]
 for f,ra,rb in pairs:
  s.frame_set(f); bpy.context.view_layer.update(); deps=bpy.context.evaluated_depsgraph_get(); ev=m.evaluated_get(deps); me=ev.to_mesh(); verts=[ev.matrix_world@v.co for v in me.vertices]
  ta=[i for i,t in enumerate(tris) if any(v in regions[ra] for v in t)]; tb=[i for i,t in enumerate(tris) if any(v in regions[rb] for v in t)]
  shared=set(ta)&set(tb); treea=BVHTree.FromPolygons(verts,[tris[i] for i in ta],all_triangles=True); treeb=BVHTree.FromPolygons(verts,[tris[i] for i in tb],all_triangles=True); ov=treea.overlap(treeb); ev.to_mesh_clear()
  rows.append({'frame':f,'region_a':ra,'region_b':rb,'triangles_a':len(ta),'triangles_b':len(tb),'shared_triangle_count':len(shared),'detailed_overlap_count':len(ov),'classification':'POTENTIAL_TRUE' if ov else 'PROXY_FALSE_POSITIVE'})
 Path(a.report).write_text(json.dumps({'status':'TARGETED_PAIR_DIAGNOSTIC','pairs':rows,'note':'Targeted mesh BVH only; no full-mesh claim.'},indent=2),encoding='utf-8'); print(json.dumps(rows,indent=2))
if __name__=='__main__': main()
