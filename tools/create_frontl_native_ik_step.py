import bpy, json, sys
from pathlib import Path
from mathutils import Vector

src, out_blend, out_report = sys.argv[sys.argv.index('--') + 1:]
bpy.ops.wm.open_mainfile(filepath=str(Path(src).resolve()))
scene=bpy.context.scene
arm=bpy.data.objects['CrimsonSpineBehemoth_Rig']
mesh=bpy.data.objects['CrimsonSpineBehemoth_Mesh']
names=['Leg_Front.L_01','Leg_Front.L_02','Leg_Front.L_03']
anatomy={'hip':'Leg_Front.L_01','knee':'Leg_Front.L_02','ankle_foot':'Leg_Front.L_03'}

scene.frame_set(1); bpy.context.view_layer.update()
pbs=[arm.pose.bones[n] for n in names]
rest_foot=arm.matrix_world @ pbs[-1].tail
rest_knee=arm.matrix_world @ pbs[1].head
rest_dirs={n:(arm.matrix_world@arm.pose.bones[n].tail-arm.matrix_world@arm.pose.bones[n].head).normalized() for n in names}

target=bpy.data.objects.new('CMAI_Temp_FrontL_Foot_Target',None); bpy.context.collection.objects.link(target)
pole=bpy.data.objects.new('CMAI_Temp_FrontL_Knee_Pole',None); bpy.context.collection.objects.link(pole)
target.empty_display_type='SPHERE'; target.empty_display_size=0.04; pole.empty_display_type='CUBE'; pole.empty_display_size=0.04
target.location=rest_foot
pole.location=rest_knee + Vector((0.0,0.0,0.35))

con=arm.pose.bones[names[-1]].constraints.new('IK'); con.name='CMAI_Temp_FrontL_NativeIK'; con.target=target; con.pole_target=pole; con.chain_count=3; con.influence=1.0

offsets={1:(0,0,0),5:(0,-0.04,0),9:(0,-0.02,0.07),13:(0,0.04,0.12),17:(0,0.09,0.07),21:(0,0.11,0.0),25:(0,0,0)}
for f,off in offsets.items():
    scene.frame_set(f); target.location=rest_foot+Vector(off); target.keyframe_insert('location',frame=f)
    pole.keyframe_insert('location',frame=f)
    con.influence = 0.0 if f in (1,25) else 1.0
    con.keyframe_insert('influence', frame=f)
    bpy.context.view_layer.update()

action=arm.animation_data.action if arm.animation_data else None
if action: action.name='CMAI_FrontL_NativeIK_Step'
for o in (target,pole): o.hide_render=True
scene.frame_start=1; scene.frame_end=25; scene.render.fps=24

results=[]
for f in [1,5,9,13,17,21,25]:
    scene.frame_set(f); bpy.context.view_layer.update()
    foot=arm.matrix_world@arm.pose.bones[names[-1]].tail
    dirs={n:(arm.matrix_world@arm.pose.bones[n].tail-arm.matrix_world@arm.pose.bones[n].head).normalized() for n in names}
    angles={n:rest_dirs[n].angle(dirs[n])*180/3.141592653589793 for n in names}
    results.append({'frame':f,'target_world':list(target.matrix_world.translation),'foot_world':list(foot),'target_error':float((foot-target.matrix_world.translation).length),'segment_direction_change_degrees':angles})

scene['cmai_anatomy_mapping']=json.dumps(anatomy)
scene['cmai_native_ik_test']='temporary_frontL_only'
bpy.ops.wm.save_as_mainfile(filepath=str(Path(out_blend).resolve()))
Path(out_report).write_text(json.dumps({'status':'NATIVE_IK_FRONTL_DIAGNOSTIC','anatomy_mapping':anatomy,'temporary_controls':[target.name,pole.name],'poses':results,'other_legs':'unchanged','baseline_frames':[1,25]},indent=2),encoding='utf-8')
print(json.dumps(results,indent=2))
