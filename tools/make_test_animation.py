"""Create and render a small visible pose test on the generated rig."""
import bpy
from pathlib import Path
from mathutils import Euler

INPUT = r"C:\Users\rober\CreatureMotionAI\data\generated\behemoth_generated_rigged.blend"
OUTPUT = r"C:\Users\rober\CreatureMotionAI\data\generated\behemoth_test_animation.blend"
RENDER_DIR = r"C:\Users\rober\CreatureMotionAI\data\generated\screenshots"

bpy.ops.wm.open_mainfile(filepath=INPUT)
rig = bpy.data.objects["CMAI_Generated_Skeleton"]
action = bpy.data.actions.new("CMAI_Behemoth_Test_Walk")
action.use_fake_user = True
rig.animation_data_create()
rig.animation_data.action = action

targets = [
    ("Leg_Front.L_01", 0.0, 0.35),
    ("Leg_Front.L_02", 0.0, -0.25),
    ("Leg_Front.R_01", 0.0, -0.35),
    ("Leg_Front.R_02", 0.0, 0.25),
    ("Tail_02", 0.0, 0.12),
]
for frame, phase in ((1, 0.0), (12, 1.0), (24, 0.0)):
    for name, base, amount in targets:
        bone = rig.pose.bones.get(name)
        if not bone:
            continue
        bone.rotation_mode = "XYZ"
        bone.rotation_euler = Euler((0.0, amount * phase, base), "XYZ")
        bone.keyframe_insert("rotation_euler", frame=frame)

scene = bpy.context.scene
scene.frame_start, scene.frame_end = 1, 24
scene.render.engine = "BLENDER_WORKBENCH"
camera_data = bpy.data.cameras.new("CMAI_Test_Camera")
camera = bpy.data.objects.new("CMAI_Test_Camera", camera_data)
bpy.context.collection.objects.link(camera)
camera.location = (3.4, 0.0, 0.45)
target = bpy.data.objects.get("CrimsonSpineBehemoth_Mesh")
target_point = target.location if target else (0.0, 0.0, 0.0)
camera.rotation_euler = (target_point - camera.location).to_track_quat("-Z", "Y").to_euler()
camera.data.lens = 52
scene.camera = camera
scene.render.resolution_x, scene.render.resolution_y = 960, 540
scene.render.resolution_percentage = 100
Path(RENDER_DIR).mkdir(parents=True, exist_ok=True)
scene.render.filepath = RENDER_DIR + r"\frame_"
for frame in (1, 12, 24):
    scene.frame_set(frame)
    scene.render.filepath = RENDER_DIR + f"\\frame_{frame:03d}.png"
    bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=OUTPUT)
print("Saved", OUTPUT)
