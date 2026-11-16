"""Non-destructive seamless-loop creation for Blender Actions."""
import json
from pathlib import Path

import bpy
from mathutils import Vector


def _channelbag(action):
    if hasattr(action, 'layers'):
        for layer in action.layers:
            for strip in layer.strips:
                for bag in strip.channelbags:
                    return bag
    return None


def _fcurves(action):
    bag = _channelbag(action)
    if bag is not None:
        return list(bag.fcurves)
    return list(getattr(action, 'fcurves', []))


def _value_at(action, data_path, index, frame):
    for fc in _fcurves(action):
        if fc.data_path == data_path and fc.array_index == index:
            return float(fc.evaluate(frame))
    return None


def _set_endpoint(action, start, end):
    changed = 0
    for fc in _fcurves(action):
        value = fc.evaluate(start)
        point = next((p for p in fc.keyframe_points if abs(p.co.x - end) < 1e-4), None)
        if point is None:
            fc.keyframe_points.insert(end, value)
        else:
            point.co.y = value
        fc.update()
        changed += 1
    return changed


def _root_motion(scene, arm, start, end):
    scene.frame_set(start); bpy.context.view_layer.update()
    a = arm.matrix_world.translation.copy()
    root_a = arm.pose.bones[arm.data.bones[0].name].matrix.copy() if arm.data.bones else None
    scene.frame_set(end); bpy.context.view_layer.update()
    b = arm.matrix_world.translation.copy()
    root_b = arm.pose.bones[arm.data.bones[0].name].matrix.copy() if arm.data.bones else None
    delta = max((abs(float(x)-float(y)) for row_a,row_b in zip(root_a, root_b) for x,y in zip(row_a,row_b)), default=0.0) if root_a and root_b else 0.0
    return {
        'armature_translation_start': list(a),
        'armature_translation_end': list(b),
        'armature_translation_delta': list(b-a),
        'root_pose_matrix_delta_max': delta,
        'classification': 'TRAVELING_ROOT' if (b-a).length > 1e-6 else 'IN_PLACE_OR_JOINT_ONLY',
    }


def _mesh_snapshot(scene):
    deps = bpy.context.evaluated_depsgraph_get()
    pts = []
    for obj in scene.objects:
        if obj.type == 'MESH':
            ev = obj.evaluated_get(deps)
            pts.extend(Vector(v.co) for v in ev.data.vertices)
    return pts


def create_loop(scene, arm, output_dir, mode='IN_PLACE'):
    if arm.animation_data is None or arm.animation_data.action is None:
        raise ValueError('The selected armature has no active Action.')
    source = arm.animation_data.action
    start = int(round(source.frame_range[0]))
    end = int(round(source.frame_range[1]))
    if end <= start:
        raise ValueError(f'Action range {source.frame_range} is not a usable cycle.')

    old_frame = scene.frame_current
    root = _root_motion(scene, arm, start, end)
    source_name = source.name
    duplicate = source.copy()
    suffix = '_SeamlessLoop_InPlace' if mode == 'IN_PLACE' else '_SeamlessLoop_Traveling'
    duplicate.name = source_name + suffix
    arm.animation_data.action = duplicate
    if duplicate.slots and hasattr(arm.animation_data, 'action_slot'):
        arm.animation_data.action_slot = duplicate.slots[0]

    # In-place mode removes only root-object translation curves; joint pose curves
    # and the original source Action remain unchanged. Traveling mode preserves all.
    removed_root_curves = 0
    if mode == 'IN_PLACE':
        for fc in list(_fcurves(duplicate)):
            if fc.data_path.startswith(('location', 'delta_location')):
                bag = _channelbag(duplicate)
                curves = bag.fcurves if bag is not None else duplicate.fcurves
                try:
                    curves.remove(fc)
                    removed_root_curves += 1
                except Exception:
                    pass
    changed = _set_endpoint(duplicate, start, end)
    scene.frame_set(start); bpy.context.view_layer.update(); first = _mesh_snapshot(scene)
    scene.frame_set(end); bpy.context.view_layer.update(); last = _mesh_snapshot(scene)
    endpoint_error = max(((a-b).length for a,b in zip(first,last)), default=0.0)
    scene.frame_set(old_frame); bpy.context.view_layer.update()

    out = Path(bpy.path.abspath(output_dir or '//cmai_loop_outputs'))
    out.mkdir(parents=True, exist_ok=True)
    blend = out / 'seamless_loop.blend'
    profile = out / 'seamless_loop_profile.json'
    report = out / 'loop_continuity_report.json'
    result = {
        'status': 'PASS' if endpoint_error < 1e-5 else 'FAIL',
        'source_action': source_name,
        'duplicate_action': duplicate.name,
        'mode': mode,
        'cycle_start': start,
        'cycle_end': end,
        'fcurves_updated': changed,
        'root_motion': root,
        'root_location_curves_removed': removed_root_curves,
        'endpoint_mesh_error': endpoint_error,
        'original_action_preserved': source_name in bpy.data.actions and source != duplicate,
        'mechanical_validation': 'PENDING_EXTERNAL_RUN',
        'limitation': 'Visual gait quality and full collision clearance still require rendered review.'
    }
    profile.write_text(json.dumps({**result, 'blend_file': str(blend)}, indent=2), encoding='utf-8')
    report.write_text(json.dumps(result, indent=2), encoding='utf-8')
    bpy.ops.wm.save_as_mainfile(filepath=str(blend), copy=True)
    return result, blend, report, profile
