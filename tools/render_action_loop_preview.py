"""Render a looping preview of an existing armature Action without saving edits."""
import argparse
import sys
from pathlib import Path

import bpy

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
parser = argparse.ArgumentParser()
parser.add_argument("--action", required=True)
parser.add_argument("--output-dir", required=True)
parser.add_argument("--seconds", type=float, default=5.0)
parser.add_argument("--fps", type=int, default=30)
args = parser.parse_args(argv)

arm = bpy.data.objects.get("CrimsonWingedDragon_Rig") or next(
    (obj for obj in bpy.data.objects if obj.type == 'ARMATURE'), None)
if arm is None or arm.animation_data is None:
    raise RuntimeError("Expected an armature with animation data")
action = bpy.data.actions.get(args.action)
if action is None:
    raise RuntimeError(f"Action not found: {args.action}")
scene = bpy.context.scene
if scene.camera is None:
    raise RuntimeError("Scene has no camera for preview rendering")

prior_action = arm.animation_data.action
prior_slot = getattr(arm.animation_data, "action_slot", None)
prior_frame = scene.frame_current
prior_path = scene.render.filepath
prior_percentage = scene.render.resolution_percentage
prior_fps = scene.render.fps
prior_fps_base = scene.render.fps_base
outdir = Path(args.output_dir)
outdir.mkdir(parents=True, exist_ok=True)
start, end = map(int, action.frame_range)
source_count = end - start + 1
frame_count = round(args.seconds * args.fps)
try:
    arm.animation_data.action = action
    slots = getattr(action, "slots", None)
    if slots and len(slots):
        try:
            arm.animation_data.action_slot = next((s for s in slots if s.target_id_type == 'OBJECT'), slots[0])
        except (AttributeError, TypeError):
            pass
    scene.render.fps = args.fps
    scene.render.fps_base = 1.0
    scene.render.resolution_percentage = min(prior_percentage, 65)
    for out_index in range(frame_count):
        scene.frame_set(start + (out_index % source_count))
        scene.render.filepath = str(outdir / f"frame_{out_index + 1:04d}.png")
        bpy.ops.render.render(write_still=True)
finally:
    arm.animation_data.action = prior_action
    if prior_slot is not None:
        try: arm.animation_data.action_slot = prior_slot
        except (AttributeError, TypeError): pass
    scene.frame_set(prior_frame)
    scene.render.filepath = prior_path
    scene.render.resolution_percentage = prior_percentage
    scene.render.fps = prior_fps
    scene.render.fps_base = prior_fps_base
print(f"ACTION_LOOP_RENDER_PASS action={action.name} rendered_frames={frame_count} source_frames={source_count} output={outdir}")
