import bpy, json
from pathlib import Path

fbx = Path(r'C:\Users\rober\Desktop\MESH2MOTION_FBX_TEXTURES\CrimsonSpineBehemoth\CrimsonSpineBehemoth_Animated.fbx')
source = Path(r'C:\Users\rober\Desktop\cmai_balisk_eight_leg_walk_repaired_clean.blend')
out = Path(r'C:\Users\rober\CreatureMotionAI\data\generated\CrimsonSpineBehemoth_CMAI_EightLeg_Walk.blend')
report_path = out.with_suffix('.json')

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=str(fbx), automatic_bone_orientation=False)
armatures = [o for o in bpy.data.objects if o.type == 'ARMATURE']
target = armatures[0] if armatures else None
if target is None:
    raise RuntimeError('No armature found in imported FBX')

before = {b.name for b in target.data.bones}
with bpy.data.libraries.load(str(source), link=False) as (data_from, data_to):
    wanted = 'CMAI_Balisk_EightLeg_Walk'
    if wanted not in data_from.actions:
        raise RuntimeError(f'Missing source Action: {wanted}')
    data_to.actions = [wanted]
action = data_to.actions[0]
action.name = 'CMAI_Balisk_EightLeg_Walk_FBX'

paths = []
curve_count = 0
for layer in action.layers:
    for strip in layer.strips:
        for bag in strip.channelbags:
            for fc in bag.fcurves:
                curve_count += 1
                if fc.data_path.startswith('pose.bones['):
                    paths.append(fc.data_path)
target.animation_data_create()
target.animation_data.action = action

for obj in bpy.data.objects:
    if obj.get('cmai_proxy') or obj.name.startswith(('CMAI_PROXY', 'CMAI_')):
        obj.hide_viewport = True
        obj.hide_render = True
for obj in armatures:
    obj.show_name = False
    obj.show_in_front = True
    obj.display_type = 'WIRE'

scene = bpy.context.scene
scene.frame_start = 1
scene.frame_end = 24
scene.render.fps = 24
bpy.ops.wm.save_as_mainfile(filepath=str(out))
report = {
    'status': 'ACTION_ASSIGNED_TO_IMPORTED_FBX',
    'source_fbx': str(fbx),
    'source_blend': str(source),
    'output_blend': str(out),
    'target_armature': target.name,
    'target_bone_count': len(before),
    'source_action': wanted,
    'assigned_action': action.name,
    'action_fcurve_count': curve_count,
    'animated_bone_paths': sorted(set(paths)),
    'note': 'Action was assigned by existing bone names; mesh deformation must be visually checked in Blender.'
}
report_path.write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps(report))
