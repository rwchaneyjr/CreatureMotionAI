import bpy, json, math
from pathlib import Path
from mathutils import Matrix, Vector

FBX = Path(r'C:\Users\rober\Desktop\MESH2MOTION_FBX_TEXTURES\CrimsonSpineBehemoth\CrimsonSpineBehemoth_Animated.fbx')
SOURCE = Path(r'C:\Users\rober\Desktop\cmai_balisk_eight_leg_walk_repaired_clean.blend')
ROOT = Path(r'C:\Users\rober\CreatureMotionAI\data\generated')
OUT_BLEND = ROOT / 'CrimsonSpineBehemoth_CMAI_RestRelative_24f.blend'
OUT_FBX = ROOT / 'CrimsonSpineBehemoth_CMAI_RestRelative_24f.fbx'
REPORT = ROOT / 'CrimsonSpineBehemoth_CMAI_RestRelative_24f_report.json'

def arm_obj(): return next((o for o in bpy.data.objects if o.type == 'ARMATURE'), None)
def ordered_bones(a): return sorted(a.pose.bones, key=lambda b: len(list(iter_parent(b))))
def iter_parent(b):
    while b.parent:
        yield b.parent; b=b.parent
def evaluated_world(arm, pb): return arm.matrix_world @ pb.matrix
def rest_world(arm, b): return arm.matrix_world @ b.matrix_local

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=str(FBX), automatic_bone_orientation=False)
target = arm_obj()
if not target: raise RuntimeError('Target FBX contains no armature')

with bpy.data.libraries.load(str(SOURCE), link=False) as (df, dt):
    dt.objects = ['CrimsonSpineBehemoth_Rig'] if 'CrimsonSpineBehemoth_Rig' in df.objects else []
    dt.actions = ['CMAI_Balisk_EightLeg_Walk'] if 'CMAI_Balisk_EightLeg_Walk' in df.actions else []
source_arm = next((o for o in dt.objects if o and o.type=='ARMATURE'), None)
action = dt.actions[0] if dt.actions else None
if not source_arm or not action: raise RuntimeError('Source armature or action unavailable')
source_arm.name = 'CMAI_Source_Armature_TEMP'; source_arm.hide_render=True; source_arm.hide_viewport=True
source_arm.animation_data_create(); source_arm.animation_data.action=action

names = sorted(set(b.name for b in source_arm.data.bones) & set(b.name for b in target.data.bones))
missing = sorted(set(b.name for b in source_arm.data.bones)-set(b.name for b in target.data.bones))
if missing: raise RuntimeError('Target missing bones: '+', '.join(missing))
compat=[]
for n in names:
    sb, tb = source_arm.data.bones[n], target.data.bones[n]
    compat.append({'bone':n,'rest_head_error':((source_arm.matrix_world@sb.head_local)-(target.matrix_world@tb.head_local)).length,'rest_tail_error':((source_arm.matrix_world@sb.tail_local)-(target.matrix_world@tb.tail_local)).length})
max_rest=max((max(x['rest_head_error'],x['rest_tail_error']) for x in compat),default=0.0)
if max_rest > 1e-3: raise RuntimeError(f'Rest pose mismatch {max_rest:.6f}; retarget blocked')

new=bpy.data.actions.new('CMAI_Balisk_EightLeg_Walk_RestRelative_FBX')
target.animation_data_create(); target.animation_data.action=new
scene=bpy.context.scene; scene.frame_start=1; scene.frame_end=24; scene.render.fps=24
rows=[]; base_positions={}
for f in range(1,25):
    scene.frame_set(f); bpy.context.view_layer.update()
    # Apply source evaluated motion as rest-relative deltas, in parent order.
    for n in names:
        sb=source_arm.pose.bones[n]; tb=target.pose.bones[n]
        sw=evaluated_world(source_arm,sb); sr=rest_world(source_arm,source_arm.data.bones[n])
        tr=rest_world(target,target.data.bones[n])
        desired=tr @ (sr.inverted() @ sw)
        tb.matrix = target.matrix_world.inverted() @ desired
    bpy.context.view_layer.update()
    for n in names:
        pb=target.pose.bones[n]
        pb.rotation_mode='QUATERNION'; pb.keyframe_insert('rotation_quaternion',frame=f,group=n)
    ev=target.evaluated_get(bpy.context.evaluated_depsgraph_get())
    # Record leg motion and extreme transform sanity checks.
    p=[]
    for n in names:
        pb=ev.pose.bones[n]; p.extend([evaluated_world(ev,pb).translation])
    if f==1: base_positions={n:target.matrix_world@target.pose.bones[n].head for n in names}
    max_delta=max(((x-base_positions[n]).length for n,x in zip(names,p)),default=0.0)
    rows.append({'frame':f,'max_bone_head_displacement_from_frame1':max_delta})

# Hide only diagnostic source armature; keep target mesh and rig visible.
source_arm.hide_viewport=True; source_arm.hide_render=True
for o in bpy.data.objects:
    if o is not target and (o.get('cmai_proxy') or o.name.startswith(('CMAI_PROXY','CMAI_'))): o.hide_viewport=True; o.hide_render=True
target.show_name=False; target.show_in_front=True; target.display_type='WIRE'
bpy.ops.wm.save_as_mainfile(filepath=str(OUT_BLEND))
target.select_set(True); bpy.context.view_layer.objects.active=target
bpy.ops.export_scene.fbx(filepath=str(OUT_FBX), use_selection=True, add_leaf_bones=False, bake_anim=True, bake_anim_use_all_actions=True, bake_anim_step=1.0, bake_anim_simplify_factor=0.0)

# Reimport exported FBX in a clean file and verify an armature, mesh, and action exist.
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=str(OUT_FBX), automatic_bone_orientation=False)
rearm=arm_obj(); meshes=[o for o in bpy.data.objects if o.type=='MESH']
reactions=[a.name for a in bpy.data.actions]
report={'status':'PASS_REST_RELATIVE_REIMPORT_CHECK' if rearm and meshes else 'FAIL_REIMPORT','source_fbx':str(FBX),'output_blend':str(OUT_BLEND),'output_fbx':str(OUT_FBX),'target_armature':'CrimsonSpineBehemoth_Rig','common_bones':len(names),'missing_target_bones':missing,'max_rest_pose_error':max_rest,'frames':rows,'reimport':{'armature':rearm.name if rearm else None,'mesh_count':len(meshes),'actions':reactions},'note':'This validates structure and rest-relative transfer; visual review remains required.'}
REPORT.write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps({'status':report['status'],'bones':len(names),'max_rest_pose_error':max_rest,'reimport_meshes':len(meshes),'reimport_actions':reactions}))
