"""Prepare a new sidebar test file in background mode; original Actions untouched."""
import json
import sys
from pathlib import Path
import bpy
import addon_utils

assert bpy.app.background, 'Prepare in background mode, then open normally'
root=Path(__file__).resolve().parents[1]
installed=Path.home()/'AppData/Roaming/Blender Foundation/Blender/5.2/scripts/addons'
sys.path=[p for p in sys.path if p and Path(p).resolve()!=root]
sys.path.insert(0,str(installed))
bpy.ops.wm.open_mainfile(filepath=str(root/'data/generated/installed_sidebar_review_20261115/sidebar_review.blend'))
addon_utils.enable('creature_motion_ai',default_set=True,persistent=True)
import creature_motion_ai
assert Path(creature_motion_ai.__file__).is_relative_to(installed)
props=bpy.context.scene.cmai_walk
props.shared_manifest=str(root/'data/generated/sidebar_camera_refit_tests/camera_refit_fd7b8bfdaf/evidence_3035a0e2ae/workflow_manifest.json')
props.auto_reference_pose=True
props.reference_pose_status='NOT TESTED'
for obj in bpy.context.scene.objects:
    if obj.type=='ARMATURE': obj.data.show_names=False
out=root/'data/generated/pose_acceptance_20261116/sidebar_acceptance.blend'
if out.exists(): raise ValueError('Review file exists; preserve it')
bpy.ops.wm.save_as_mainfile(filepath=str(out))
print('Prepared',out,'using installed module',creature_motion_ai.__file__)
