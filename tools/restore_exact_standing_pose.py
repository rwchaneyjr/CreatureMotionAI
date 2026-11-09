import bpy, json, sys
from pathlib import Path
from mathutils import Matrix

src, out_blend, out_report, render_dir = sys.argv[sys.argv.index('--') + 1:]
src=Path(src).resolve(); out_blend=Path(out_blend).resolve(); out_report=Path(out_report).resolve(); render_dir=Path(render_dir).resolve(); render_dir.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(src))
s=bpy.context.scene; arm=bpy.data.objects['CrimsonSpineBehemoth_Rig']; mesh=bpy.data.objects['CrimsonSpineBehemoth_Mesh']
s.frame_set(1); bpy.context.view_layer.update()
base={p.name:p.matrix.copy() for p in arm.pose.bones}
def verts():
    deps=bpy.context.evaluated_depsgraph_get(); em=mesh.evaluated_get(deps); me=em.to_mesh(); out=[arm.matrix_world @ mesh.matrix_world.inverted() @ v.co for v in me.vertices]; em.to_mesh_clear(); return out
base_v=verts()
old_action=arm.animation_data.action if arm.animation_data else None
old_nla=[(t,s,m) for t in (arm.animation_data.nla_tracks if arm.animation_data else []) for s in t.strips for m in (s.mute,)]
for _,strip,_ in old_nla: strip.mute=True
if arm.animation_data: arm.animation_data.action=None
action=bpy.data.actions.new('CMAI_Exact_Standing_Baseline_24F'); action.use_fake_user=True; arm.animation_data_create(); arm.animation_data.action=action
def apply_and_key(frame):
    for p in arm.pose.bones: p.matrix=base[p.name]
    s.frame_set(frame); bpy.context.view_layer.update()
    for p in arm.pose.bones:
        p.keyframe_insert(data_path='rotation_mode',frame=frame)
        if p.rotation_mode=='QUATERNION': p.keyframe_insert(data_path='rotation_quaternion',frame=frame)
        else: p.keyframe_insert(data_path='rotation_euler',frame=frame)
    bpy.context.view_layer.update()
    vv=verts(); pv={p.name:p.matrix.copy() for p in arm.pose.bones}
    return pv,vv
p1,v1=apply_and_key(1); p25,v25=apply_and_key(25)
def materr(a,b): return max((a[n]-b[n]).to_translation().length for n in a)
def verror(v): return max((a-b).length for a,b in zip(v,base_v))
s.frame_start=1; s.frame_end=25; s.render.fps=24; s.render.engine='BLENDER_WORKBENCH'; s.render.resolution_x=960; s.render.resolution_y=540; s.render.resolution_percentage=100; s.render.image_settings.file_format='PNG'
cam=next((o for o in s.objects if o.type=='CAMERA'),None); s.camera=cam
for f in (1,25):
    s.frame_set(f); s.render.filepath=str(render_dir/f'frame_{f:02d}.png'); bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=str(out_blend))
report={'status':'EXACT_STANDING_BASELINE_TEST','source':str(src),'output':str(out_blend),'frame1_match':'PASS' if materr(p1,base)<1e-6 and verror(v1)<1e-6 else 'FAIL','frame25_match':'PASS' if materr(p25,base)<1e-6 and verror(v25)<1e-6 else 'FAIL','max_bone_matrix_difference_frame1':materr(p1,base),'max_bone_matrix_difference_frame25':materr(p25,base),'max_mesh_vertex_displacement_frame1':verror(v1),'max_mesh_vertex_displacement_frame25':verror(v25),'previous_action':old_action.name if old_action else None,'nla_strips_muted_temporarily':len(old_nla),'original_assets_preserved':True}
out_report.write_text(json.dumps(report,indent=2),encoding='utf-8'); print(json.dumps(report))
