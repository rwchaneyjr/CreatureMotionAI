"""Launch a disposable review scene using the installed, not workspace, add-on."""
import json
import sys
from pathlib import Path
import bpy
import addon_utils

# Opening/saving a file during interactive command-line startup can run before
# Blender has a window/screen and has crashed in this review harness. Prepare
# the disposable file in background mode, then open it normally in the UI.
if not bpy.app.background:
    raise RuntimeError('Prepare this review file with Blender -b, then open the saved .blend normally. No scene changed.')

root=Path(__file__).resolve().parents[1]
installed=Path.home()/'AppData/Roaming/Blender Foundation/Blender/5.2/scripts/addons'
sys.path=[p for p in sys.path if p and Path(p).resolve()!=root]
sys.path.insert(0,str(installed))
baseline=root/'data/generated/e2e_balisk_test/rear_baseline_builder/rear_baseline_fixed_mapping.blend'
bpy.ops.wm.open_mainfile(filepath=str(baseline))
addon_utils.enable('creature_motion_ai',default_set=True,persistent=True)
import creature_motion_ai
assert Path(creature_motion_ai.__file__).is_relative_to(installed)
s=bpy.context.scene; p=s.cmai_walk
p.project_folder=str(root); p.rig=next(o for o in s.objects if o.type=='ARMATURE')
p.external_python=str(root/'.venv-dlc/Scripts/python.exe')
p.profile_path=str(root/'creature_motion_ai/profiles/balisk_reference_walk.json')
p.shared_manifest=str(root/'data/generated/sidebar_camera_refit_tests/camera_refit_fd7b8bfdaf/workflow_manifest.json')
p.side_video='C:/Users/rober/Downloads/8leggedSIDEbalaskWALK.mp4'
p.front_video='C:/Users/rober/Downloads/8leggedBaliskfrontwalk.mp4'
p.best_animation=str(baseline); p.standing_model=str(root/'data/generated/cmai_exact_standing_baseline_24f.blend')
out=root/'data/generated/installed_sidebar_review_20261115'; out.mkdir(exist_ok=True)
p.output=str(out)
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type=='VIEW_3D':
            area.spaces.active.show_region_ui=True
            area.spaces.active.shading.type='SOLID'
bpy.ops.wm.save_as_mainfile(filepath=str(out/'sidebar_review.blend'),copy=False)
(out/'installed_module.json').write_text(json.dumps({'module':creature_motion_ai.__file__,'source_baseline':str(baseline),'original_action':p.rig.animation_data.action.name,'review_scene':bpy.data.filepath},indent=2))
