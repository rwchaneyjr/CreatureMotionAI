import argparse, subprocess
from pathlib import Path
def main():
 p=argparse.ArgumentParser(); p.add_argument('--blender',required=True); p.add_argument('--blend',required=True); p.add_argument('--report',required=True); a=p.parse_args(); rp=str(Path(a.report).resolve()).replace('\\','/')
 expr=f'''import bpy,json,math,statistics
bpy.ops.wm.open_mainfile(filepath=r"{Path(a.blend).resolve()}"); s=bpy.context.scene; arm=next(o for o in bpy.data.objects if o.type=='ARMATURE'); mesh=next(o for o in bpy.data.objects if o.type=='MESH'); deps=bpy.context.evaluated_depsgraph_get(); action=arm.animation_data.action if arm.animation_data else None; names=['Leg_Front.L_01','Leg_Front.L_02','Leg_Front.L_03']; groups={{mesh.vertex_groups[n].index for n in names if mesh.vertex_groups.get(n)}}; ids=[v.index for v in mesh.data.vertices if any(g.group in groups and g.weight>.25 for g in v.groups)]
def snap():
 deps.update(); ev=mesh.evaluated_get(deps); me=ev.to_mesh(); pts=[ev.matrix_world@me.vertices[i].co for i in ids]; ev.to_mesh_clear(); bones={{n:{{'head':list(arm.matrix_world@arm.pose.bones[n].head),'tail':list(arm.matrix_world@arm.pose.bones[n].tail),'rot':list(arm.pose.bones[n].rotation_quaternion)}} for n in names}}; foot=list(arm.matrix_world@arm.pose.bones[names[-1]].tail); return pts,bones,foot
frames={{}}; curves=[]
if action:
 for layer in action.layers:
  for strip in layer.strips:
   for bag in strip.channelbags:
    for fc in bag.fcurves:
     if any(n in fc.data_path for n in names): curves.append({{'path':fc.data_path,'points':len(fc.keyframe_points)}})
for f in (1,12,18,24): s.frame_set(f); bpy.context.view_layer.update(); frames[f]=snap()
base=frames[1][0]; rows=[]
for f,(pts,bones,foot) in frames.items():
 ds=[(p-base[i]).length for i,p in enumerate(pts)]; rows.append({{'frame':f,'foot':foot,'foot_displacement':math.dist(foot,frames[1][2]),'bones':bones,'max_vertex_displacement':max(ds),'mean_vertex_displacement':statistics.mean(ds),'p95_vertex_displacement':sorted(ds)[int(.95*len(ds))-1],'moving_vertices_gt_1e-4':sum(x>1e-4 for x in ds)}})
out={{'status':'front_fk_displacement_complete','action':action.name if action else None,'action_assigned_to':arm.name,'fcurves':curves,'weighted_vertices':len(ids),'frames':rows,'ground_penetration':'checked_in_front_fk_validation.json','collision':'NOT_TESTED_BVH','anatomical_validity':'REQUIRES_VISUAL_REVIEW'}}
open(r'{rp}','w').write(json.dumps(out,indent=2)); print(json.dumps({{'status':out['status'],'action':out['action'],'fcurves':len(curves),'weighted_vertices':len(ids),'frames':rows}}))'''
 subprocess.run([a.blender,'--background','--python-expr',expr],check=True)
if __name__=='__main__': main()
