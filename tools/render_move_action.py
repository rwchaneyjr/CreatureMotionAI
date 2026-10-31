"""Transfer the source FBX Move action to the generated rig and render samples."""
import bpy
from pathlib import Path

INPUT = r"C:\Users\rober\CreatureMotionAI\data\generated\behemoth_generated_rigged.blend"
OUTPUT = r"C:\Users\rober\CreatureMotionAI\data\generated\behemoth_move_action.blend"
RENDER_DIR = r"C:\Users\rober\CreatureMotionAI\data\generated\move_screenshots"

bpy.ops.wm.open_mainfile(filepath=INPUT)
rig = bpy.data.objects["CMAI_Generated_Skeleton"]
move = next(action for action in bpy.data.actions if action.name.endswith("|Move"))
rig.animation_data_create()
rig.animation_data.action = move
scene = bpy.context.scene
scene.frame_start, scene.frame_end = 1, int(move.frame_range[1])
scene.render.engine = "BLENDER_WORKBENCH"
camera_data = bpy.data.cameras.new("CMAI_Move_Camera")
camera = bpy.data.objects.new("CMAI_Move_Camera", camera_data)
bpy.context.collection.objects.link(camera)
camera.location = (3.4, 0.0, 0.45)
target = bpy.data.objects.get("CrimsonSpineBehemoth_Mesh")
camera.rotation_euler = (target.location - camera.location).to_track_quat("-Z", "Y").to_euler()
camera.data.lens = 52
scene.camera = camera
scene.render.resolution_x, scene.render.resolution_y = 960, 540
scene.render.resolution_percentage = 100
Path(RENDER_DIR).mkdir(parents=True, exist_ok=True)
for frame in (1, 24, 48, 73):
    scene.frame_set(frame)
    scene.render.filepath = RENDER_DIR + f"\\move_{frame:03d}.png"
    bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=OUTPUT)
print("Saved", OUTPUT)
