import bpy,sys,json
from pathlib import Path
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root))
import creature_motion_ai
creature_motion_ai.register()
p=bpy.context.scene.cmai_walk
p.external_python=str(root/'.venv-dlc/Scripts/python.exe');p.output=str(root/'data/generated/sidebar_camera_refit_tests')
p.standing_model=str(root/'data/generated/cmai_exact_standing_baseline_24f.blend')
p.best_animation=str(root/'data/generated/e2e_balisk_test/rear_baseline_builder/rear_baseline_fixed_mapping.blend')
p.side_video='C:/Users/rober/Downloads/8leggedSIDEbalaskWALK.mp4';p.front_video='C:/Users/rober/Downloads/8leggedBaliskfrontwalk.mp4'
if '--side-only' in sys.argv: p.front_video=''
before=[(o.name,o.type) for o in bpy.context.scene.objects]; actions=[a.name for a in bpy.data.actions]
result=bpy.ops.cmai.refit_standing_cameras()
assert result=={'FINISHED'},result
assert before==[(o.name,o.type) for o in bpy.context.scene.objects]
assert actions==[a.name for a in bpy.data.actions]
path=Path(p.shared_manifest); report={'operator':str(result),'manifest':str(path),'scene_preserved':True,'actions_preserved':True,'test_mode':'background Blender invocation of registered sidebar operator; interactive click not tested'}
(path.parent/'sidebar_test.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
