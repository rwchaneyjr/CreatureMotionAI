"""Render candidate frames for contact-lock comparison without saving scene edits."""
import bpy
from pathlib import Path

root = Path(__file__).resolve().parents[1]
out = root / "data/generated/balisk_camera_fullbody_walk_02/contact_lock_v1/candidate_frames"
out.mkdir(parents=True, exist_ok=True)
scene = bpy.context.scene
scene.camera = bpy.data.objects.get("CMAI_Video_Side_Camera") or scene.camera
if scene.camera is None:
    raise RuntimeError("Candidate blend has no side-view camera")
scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x = 1280
scene.render.resolution_y = 720
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.render.film_transparent = False
for frame in range(1, 121):
    scene.frame_set(frame)
    scene.render.filepath = str(out / f"frame_{frame:04d}.png")
    bpy.ops.render.render(write_still=True)
print(f"CONTACT_LOCK_RENDER_DONE {out}", flush=True)
