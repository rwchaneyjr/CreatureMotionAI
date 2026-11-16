import sys, json, importlib.util
from pathlib import Path
import bpy

ROOT=Path(r'C:\Users\rober\CreatureMotionAI')
OUT=ROOT/'data/generated/e2e_balisk_test/rear_baseline_builder'
OUT.mkdir(parents=True,exist_ok=True)
spec=importlib.util.spec_from_file_location('cmai_source',ROOT/'creature_motion_ai/__init__.py',submodule_search_locations=[str(ROOT/'creature_motion_ai')])
pkg=importlib.util.module_from_spec(spec); sys.modules['cmai_source']=pkg; spec.loader.exec_module(pkg)
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'data/generated/original_static_standing.blend'))
service=pkg.reference_walk; auto=pkg.auto_anatomy; scene=bpy.context.scene
arm=next(o for o in scene.objects if o.type=='ARMATURE'); mesh=next(o for o in scene.objects if o.type=='MESH')
det=auto.detect_anatomy(arm)
profile=auto.profile_from_detection(det,next(b.name for b in arm.data.bones if b.parent is None))
profile.update({'confirmed':True,'mapping_status':'E2E_TEST_CONFIRMATION_REQUIRED_IN_REAL_UI','forward_world':[0,-1,0],'body_height':0.07,'inward':0.2,'shared_stride':0.13,'lift_fraction':0.23,'body_bob':0.003,'cycle_frames':40,'duty_factor':0.65,'world_planted_support':True,'contact_xy_tolerance':0.0008,'minimum_knee_flexion_degrees':8,'maximum_knee_flexion_degrees':135,'body_bones':[]})
profile['phase_offsets']={k:i/len(profile['chains']) for i,k in enumerate(profile['chains'])}
(OUT/'anatomy_detection.json').write_text(json.dumps(det,indent=2),encoding='utf-8')
(OUT/'confirmed_profile.json').write_text(json.dumps(profile,indent=2),encoding='utf-8')
scene.frame_set(1)
anatomy=service.capture_anatomy(arm,mesh,profile)
settings={k:profile[k] for k in ['body_height','inward','shared_stride','lift_fraction','body_bob','cycle_frames','duty_factor','world_planted_support','contact_xy_tolerance','minimum_knee_flexion_degrees','maximum_knee_flexion_degrees']}
settings.update({'phase_offsets':profile['phase_offsets'],'fps':24,'validated_rear_baseline_path':str(ROOT/'data/generated/balisk_camera_baseline_walk_01/rear_trajectory_baseline.json')})
for label in ('standing','waypoints','walk','validation'):
    (OUT/label).mkdir(parents=True,exist_ok=True)
standing=service.fit_standing(scene,arm,mesh,anatomy,settings,OUT/'standing')
camera=service.setup_preview_camera(scene,mesh,profile['forward_world'],standing['ground'])
prepared=service.generate_waypoints_or_walk(scene,arm,mesh,anatomy,standing,settings,OUT/'waypoints',plan_only=True)
walk=service.generate_waypoints_or_walk(scene,arm,mesh,anatomy,standing,settings,OUT/'walk',prepared=prepared)
validation=service.validate_animation(scene,arm,mesh,anatomy,settings,standing['ground'],OUT/'validation')
(OUT/'generated_walk.blend').parent.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'generated_walk.blend'),copy=True)
loop_out=OUT/'seamless'; loop_out.mkdir(parents=True,exist_ok=True)
loop_result,loop_blend,loop_report,loop_profile=pkg.loop_service.create_loop(scene,arm,str(loop_out),'IN_PLACE')
scene.frame_start=1; scene.frame_end=120; scene.render.fps=24; scene.render.resolution_x=1280; scene.render.resolution_y=720; scene.render.resolution_percentage=100
frames=OUT/'rendered_frames'; frames.mkdir(parents=True,exist_ok=True)
scene.render.image_settings.file_format='PNG'; scene.render.filepath=str(frames/'walk_')
bpy.ops.render.render(animation=True)
result={'anatomy_detection':det,'manual_confirmation_required':True,'video_analysis':'PASS_EXTERNAL_ANALYSIS_REVIEW_REQUIRED','standing':standing,'walk':walk,'validation':validation,'camera':camera,'loop':loop_result,'generated_blend':str(OUT/'generated_walk.blend'),'loop_blend':str(loop_blend),'rendered_frames':str(frames),'note':'Fresh Action generated from automatic anatomy proposal; confirmation was injected only for this controlled end-to-end test.'}
(OUT/'e2e_builder_result.json').write_text(json.dumps(result,indent=2,default=str),encoding='utf-8')
print('E2E_BUILDER',json.dumps({'legs':det['selected_leg_count'],'standing':standing['status'],'walk':walk.get('action'),'validation':validation['status']}))
