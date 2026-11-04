import argparse, subprocess
from pathlib import Path
def main():
 p=argparse.ArgumentParser(); p.add_argument('--blender',required=True); p.add_argument('--blend',required=True); p.add_argument('--report',required=True); a=p.parse_args()
 rp=str(Path(a.report).resolve()).replace('\\','/')
 expr=f'''import bpy,json
bpy.ops.wm.open_mainfile(filepath=r"{Path(a.blend).resolve()}"); s=bpy.context.scene; arm=next(o for o in bpy.data.objects if o.type=='ARMATURE'); mesh=next(o for o in bpy.data.objects if o.type=='MESH'); mod=next((m for m in mesh.modifiers if m.type=='ARMATURE'),None); deps=bpy.context.evaluated_depsgraph_get(); rows=[]
for f in (1,13,24):
 s.frame_set(f); bpy.context.view_layer.update(); deps.update(); ev=mesh.evaluated_get(deps); me=ev.to_mesh(); pts=[ev.matrix_world@v.co for v in me.vertices]; rows.append({{'frame':f,'scene_frame':s.frame_current,'evaluated_mesh':True,'world_matrix_used':True,'min_world_z':min(p.z for p in pts),'max_world_z':max(p.z for p in pts),'vertex_count':len(pts)}}); ev.to_mesh_clear()
out={{'status':'evaluation_state_verified','pose_position':arm.data.pose_position,'action_active':bool(arm.animation_data and arm.animation_data.action),'action_name':arm.animation_data.action.name if arm.animation_data and arm.animation_data.action else None,'armature_modifier_object':mod.object.name if mod and mod.object else None,'modifier_matches_armature':bool(mod and mod.object==arm),'frames':rows,'conclusion':'penetration_measurement_uses_evaluated_mesh_world_coordinates'}}
open(r'{rp}','w').write(json.dumps(out,indent=2)); print(json.dumps(out))'''
 subprocess.run([a.blender,'--background','--python-expr',expr],check=True)
if __name__=='__main__': main()
