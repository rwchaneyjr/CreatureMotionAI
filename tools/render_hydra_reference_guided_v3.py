import bpy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "data/generated/hydra_two_view_500_pose_pilot"
BLEND = ROOT / "hydra_reference_guided_walk_5s_v3.blend"
OUT = ROOT / "candidate_v3_renders"
bpy.ops.wm.open_mainfile(filepath=str(BLEND))
scene = bpy.context.scene
arm = bpy.data.objects["SevenHeadedHydra_Rig"]
action = bpy.data.actions["CMAI_Hydra_ReferenceGuided_Walk_5s_v2"]
arm.animation_data.action = action
if action.slots and hasattr(arm.animation_data, "action_slot"):
    arm.animation_data.action_slot = action.slots[0]
scene.render.resolution_x = 480
scene.render.resolution_y = 270
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.render.film_transparent = False
scene.render.engine = "BLENDER_EEVEE"
scene.eevee.taa_render_samples = 16
OUT.mkdir(exist_ok=True)
for view, camera in [("side", "CMAI_Camera_Side_Reference"), ("front", "CMAI_Camera_Front_Reference")]:
    scene.camera = bpy.data.objects[camera]
    for frame in range(1, 121):
        scene.frame_set(frame)
        scene.render.filepath = str(OUT / f"{view}_{frame:04d}.png")
        bpy.ops.render.render(write_still=True)
        if frame % 24 == 0:
            print("RENDER_PROGRESS", view, frame, flush=True)
print("RENDER_COMPLETE", str(OUT), flush=True)
