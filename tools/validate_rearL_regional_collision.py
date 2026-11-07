"""Stable, spatially restricted Rear.L collision check."""
import argparse,json,sys
from pathlib import Path
def collect(bpy,path,frames):
 from mathutils import Vector
 from mathutils.bvhtree import BVHTree
 bpy.ops.wm.open_mainfile(filepath=str(Path(path).resolve())); scene=bpy.context.scene; mesh=next(o for o in scene.objects if o.type=='MESH'); mesh.data.calc_loop_triangles(); tris=[tuple(t.vertices) for t in mesh.data.loop_triangles]
 groups={g.index for g in mesh.vertex_groups if g.name.startswith('Leg_Rear.L_')}; legv={v.index for v in mesh.data.vertices if any(x.group in groups and x.weight>0.05 for x in v.groups)}
 scene.frame_set(1); bpy.context.view_layer.update(); deps=bpy.context.evaluated_depsgraph_get(); ev=mesh.evaluated_get(deps); d=ev.to_mesh(); verts=[ev.matrix_world@v.co for v in d.vertices]; ev.to_mesh_clear(); xs=[verts[i].x for i in legv]; ys=[verts[i].y for i in legv]; zs=[verts[i].z for i in legv]; margin=.35; lo=Vector((min(xs)-margin,min(ys)-margin,min(zs)-margin)); hi=Vector((max(xs)+margin,max(ys)+margin,max(zs)+margin))
 selected=[]
 for i,t in enumerate(tris):
  if any(v in legv for v in t): selected.append(i); continue
  c=sum((verts[v] for v in t),Vector())/3
  if lo.x<=c.x<=hi.x and lo.y<=c.y<=hi.y and lo.z<=c.z<=hi.z: selected.append(i)
 adjacency=set()
 for ai,i in enumerate(selected):
  si=set(tris[i])
  for j in selected[ai+1:]:
   if si.intersection(tris[j]): adjacency.add((min(i,j),max(i,j)))
 out={}
 for f in frames:
  scene.frame_set(f); bpy.context.view_layer.update(); deps=bpy.context.evaluated_depsgraph_get(); ev=mesh.evaluated_get(deps); d=ev.to_mesh(); vs=[ev.matrix_world@v.co for v in d.vertices]; tree=BVHTree.FromPolygons(vs,[tris[i] for i in selected],all_triangles=True); hits=set()
  for a,b in tree.overlap(tree):
   ia,ib=selected[a],selected[b]
   if ia>=ib or (min(ia,ib),max(ia,ib)) in adjacency: continue
   hits.add((ia,ib))
  out[str(f)]={'pair_count':len(hits),'pairs':[list(x) for x in sorted(hits)][:100]}; ev.to_mesh_clear()
 return out
def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--original',required=True); ap.add_argument('--animated',required=True); ap.add_argument('--report',required=True); argv=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else sys.argv[1:]; a=ap.parse_args(argv); import bpy
 base=collect(bpy,a.original,[1]); anim=collect(bpy,a.animated,list(range(1,25))); b=set(map(tuple,base['1']['pairs'])); rows=[]
 for f,v in anim.items(): s=set(map(tuple,v['pairs'])); rows.append({'frame':int(f),'baseline_pairs':len(b),'animated_pairs':len(s),'new_pairs':len(s-b),'resolved_pairs':len(b-s),'new_pair_ids':[list(x) for x in sorted(s-b)][:100]})
 result={'status':'REGIONAL_BASELINE_RELATIVE','same_source_topology':True,'region':'Leg_Rear.L plus conservative .35-unit neighborhood','resting_pose':base['1'],'frames':rows,'note':'Regional result only; not full-mesh clearance.'}; Path(a.report).write_text(json.dumps(result,indent=2),encoding='utf-8'); print(json.dumps({'rest':len(b),'max_new':max(x['new_pairs'] for x in rows)}))
if __name__=='__main__': main()
