"""Execute the registered sidebar operators in Blender on a supplied baseline."""
import bpy, sys, json, time, argparse
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser()
parser.add_argument('--addon-zip',type=Path)
args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
if args.addon_zip:
    bpy.ops.preferences.addon_install(filepath=str(args.addon_zip.resolve()),overwrite=False)
    scripts=Path(bpy.utils.user_resource('SCRIPTS'))/'addons'
    sys.path.insert(0,str(scripts))
else:
    sys.path.insert(0,str(ROOT))
import creature_motion_ai
from creature_motion_ai import reference_walk_ui as ui
from creature_motion_ai.walk_waypoints import mesh_world, fingerprint
import numpy as np

creature_motion_ai.register()
# Exercise clean registration lifecycle without touching legacy operator behavior.
creature_motion_ai.unregister(); creature_motion_ai.register()
scene=bpy.context.scene
arm=next(o for o in scene.objects if o.type=='ARMATURE')
mesh=next(o for o in scene.objects if o.type=='MESH' and any(m.type=='ARMATURE' and m.object==arm for m in o.modifiers))
scene.frame_set(1); bpy.context.view_layer.update(); original=mesh_world(mesh); digest=fingerprint(arm,mesh)
original_action=arm.animation_data.action.name if arm.animation_data and arm.animation_data.action else None
legacy=[name for name in dir(bpy.ops.cmai) if name not in ['reference_walk_step','walk_load_balisk_profile']]
result=bpy.ops.cmai.walk_load_balisk_profile(); assert result=={'FINISHED'}
scene.cmai_walk.rig=arm
scene.cmai_walk.output=str(ROOT/'data/generated/addon_walk_builder_tests')
scene.cmai_walk.external_python=str(ROOT/'.venv-dlc/Scripts/python.exe')
records=[]
for stage in ['rig','standing','standing_preview','waypoints','walk','validation','render']:
    started=time.time(); print('TEST STAGE',stage,flush=True)
    result=bpy.ops.cmai.reference_walk_step(stage=stage)
    state=ui.read_state(bpy.context.scene)
    records.append({'stage':stage,'operator_result':list(result),'status':state.get('stages',{}).get(stage),'seconds':time.time()-started,'message':state.get('message')})
    target=Path(state['run'])/'operator_integration_test.json'
    target.write_text(json.dumps({'legacy_operator_count':len(legacy),'stages':records},indent=2))
    if result!={'FINISHED'}: raise RuntimeError(f'{stage} FAILED: {state.get("message")}')
working_scene=bpy.context.scene
# Check that stale camera/curve evidence cannot authorize another render.
from creature_motion_ai import reference_walk as service
from creature_motion_ai.walk_waypoints import action_curves
working_arm,working_mesh=ui.working_objects(working_scene,state)
signature=service.motion_signature(working_scene,working_arm)
original_state=json.loads(json.dumps(state)); negative_tests={}
camera=working_scene.camera; angle=camera.rotation_euler.x
camera.rotation_euler.x+=.01
negative_tests['camera_edit_detected']=service.motion_signature(working_scene,working_arm)!=signature
try:
    bpy.ops.cmai.reference_walk_step(stage='render')
except RuntimeError:
    pass
blocked=ui.read_state(working_scene)
negative_tests['stale_render_blocked']=blocked['stages']['render']=='FAIL' and blocked['stages']['validation']=='NOT TESTED'
camera.rotation_euler.x=angle
ui.save_state(working_scene,original_state)
curve=next(c for c in action_curves(working_arm.animation_data.action) if 'rotation_quaternion' in c.data_path)
point=curve.keyframe_points[0]; value=point.co.y; point.co.y+=.01
negative_tests['curve_edit_detected']=service.motion_signature(working_scene,working_arm)!=signature
point.co.y=value
p=working_scene.cmai_walk; stride=p.stride; p.stride=stride+.001
negative_tests['settings_invalidate_walk']=ui.read_state(working_scene)['stages']['walk']=='NOT TESTED'
p.stride=stride; ui.save_state(working_scene,original_state)
negative_tests['restored_signature_matches']=service.motion_signature(working_scene,working_arm)==signature
assert all(negative_tests.values()),negative_tests
bpy.context.window.scene=scene; scene.frame_set(1); bpy.context.view_layer.update()
preserved={'geometry_hash_match':fingerprint(arm,mesh)==digest,'evaluated_source_mesh_error':float(np.linalg.norm(mesh_world(mesh)-original,axis=1).max()),
 'source_action_unchanged':(arm.animation_data.action.name if arm.animation_data and arm.animation_data.action else None)==original_action}
bpy.context.window.scene=working_scene
report={'loaded_addon_path':creature_motion_ai.__file__,'installed_zip':str(args.addon_zip) if args.addon_zip else None,
        'legacy_operator_count':len(legacy),'registration_unregister_reregister':'PASS','stages':records,'original_scene_preservation':preserved,
        'stale_validation_regressions':negative_tests,
        'pending_controls':ui.PENDING,'workflow_state':state}
target.write_text(json.dumps(report,indent=2)); print('INTEGRATION_REPORT',str(target),flush=True)
assert preserved['geometry_hash_match'] and preserved['evaluated_source_mesh_error']<1e-6 and preserved['source_action_unchanged']
