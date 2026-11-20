"""Read-only side-camera projection of the copied Rear.L chain."""
import json
import os
from pathlib import Path

import bpy
from bpy_extras.object_utils import world_to_camera_view


source = Path(os.environ["CMAI_HYBRID_BLEND"])
destination = Path(os.environ["CMAI_HYBRID_PROJECTION_REPORT"])
bpy.ops.wm.open_mainfile(filepath=str(source.resolve()))
scene = bpy.context.scene
arm = bpy.data.objects["CrimsonSpineBehemoth_Rig"]
rows = []
for frame in (1, 12, 18, 24, 30, 32):
    scene.frame_set(frame)
    chain = [arm.pose.bones[f"Leg_Rear.L_{index:02}"] for index in (1, 2, 3)]
    joints = {"hip": chain[0].head, "knee": chain[0].tail,
              "ankle": chain[1].tail, "tip": chain[2].tail}
    projected = {}
    for name, arm_local in joints.items():
        uv = world_to_camera_view(scene, scene.camera, arm.matrix_world @ arm_local)
        # Horizontal mirror to match the reference creature facing right.
        projected[name] = [round((1.0 - uv.x) * 1280, 2), round((1.0 - uv.y) * 720, 2)]
    rows.append({"frame": frame, "mirrored_original_camera_px": projected})
destination.parent.mkdir(parents=True, exist_ok=True)
destination.write_text(json.dumps(rows, indent=2), encoding="utf-8")
print(json.dumps(rows))
