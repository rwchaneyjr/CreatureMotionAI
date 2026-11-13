"""Reopen a delivered Blender copy and verify playback and a legacy operator."""
import json
import sys
import uuid
from pathlib import Path

import bpy
import numpy as np

sys.path.insert(0, str(Path(bpy.utils.user_resource('SCRIPTS')) / 'addons'))
import creature_motion_ai
from creature_motion_ai import reference_walk as service
from creature_motion_ai import reference_walk_ui as ui
from creature_motion_ai.walk_waypoints import mesh_world

creature_motion_ai.register()
scene = bpy.context.scene
state = ui.read_state(scene)
arm, mesh = ui.working_objects(scene, state)
anatomy = json.loads(Path(state['anatomy']).read_text())
validation = json.loads(Path(state['validation_report']).read_text())
root_name = anatomy['profile']['root_bone']
out = Path(state['run']) / ('reopened_' + uuid.uuid4().hex[:8])
out.mkdir()

signature_matches = service.motion_signature(scene, arm) == validation['motion_signature']
samples = []
first = None
for frame in [1, 14, 21, 36, 76, 121]:
    scene.frame_set(frame)
    bpy.context.view_layer.update()
    vertices = mesh_world(mesh)
    relative = vertices - np.array(arm.matrix_world @ arm.pose.bones[root_name].head)
    if first is None:
        first = relative.copy()
    movements = {
        leg: float(np.linalg.norm(relative[data['indices']] - first[data['indices']], axis=1).max())
        for leg, data in anatomy['legs'].items()
    }
    samples.append({'frame': frame, 'mesh_movement_relative_to_body': movements})

loop_error = float(np.linalg.norm(relative - first, axis=1).max())
all_legs_move = all(max(s['mesh_movement_relative_to_body'][leg] for s in samples) > .02
                    for leg in anatomy['legs'])
scene.frame_set(1)
bpy.context.view_layer.objects.active = arm
scene.cmai_profile_output = str(out / 'legacy_skeleton_profile.json')
legacy_result = bpy.ops.cmai.inspect_armature()
report = {
    'source_blend': bpy.data.filepath,
    'loaded_addon': creature_motion_ai.__file__,
    'saved_signature_matches': signature_matches,
    'all_eight_legs_move_after_reopening': all_legs_move,
    'loop_mesh_error': loop_error,
    'legacy_inspect_armature': list(legacy_result),
    'bone_count': len(arm.data.bones),
    'samples': samples,
}
report['status'] = 'PASS' if signature_matches and all_legs_move and loop_error < 1e-5 and legacy_result == {'FINISHED'} else 'FAIL'
service.write_json(out / 'saved_blend_playback.json', report)
print('REOPENED_REPORT', out / 'saved_blend_playback.json', flush=True)
assert report['status'] == 'PASS', report
