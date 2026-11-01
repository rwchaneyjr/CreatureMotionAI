"""Camera-only calibration and side-by-side diagnostic for one reference frame.

This intentionally starts from the clean original-pose blend and never edits the
mesh, armature, actions, or rest pose. It creates a new diagnostic blend.
"""
import argparse
import json
import subprocess
from pathlib import Path

import cv2
import numpy as np


def make_side_by_side(reference, render, output):
    ref = cv2.imread(str(reference), cv2.IMREAD_COLOR)
    img = cv2.imread(str(render), cv2.IMREAD_COLOR)
    if ref is None or img is None:
        raise RuntimeError("Could not read reference or render")
    img = cv2.resize(img, (ref.shape[1], ref.shape[0]), interpolation=cv2.INTER_AREA)
    canvas = np.hstack([ref, img])
    cv2.putText(canvas, "REFERENCE", (24, 42), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255,255,255), 2)
    cv2.putText(canvas, "BLENDER STATIC / CAMERA ONLY", (ref.shape[1] + 24, 42), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255,255,255), 2)
    cv2.imwrite(str(output), canvas)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--blend", required=True)
    p.add_argument("--reference", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--blender", required=True)
    p.add_argument("--work", required=True)
    args = p.parse_args()
    out = Path(args.output)
    work = Path(args.work)
    work.mkdir(parents=True, exist_ok=True)
    render = work / "camera_calibration_render.png"
    side_blend = work / "camera_calibrated_static.blend"
    # The model's long axis is local Y. View along local -X for the reference side view.
    expr = f"""
import bpy
from mathutils import Vector
bpy.ops.wm.open_mainfile(filepath=r'{Path(args.blend).resolve()}')
scene=bpy.context.scene
scene.render.resolution_x=1280; scene.render.resolution_y=720; scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG'
if scene.world is None:
    scene.world=bpy.data.worlds.new('CMAI_Calibration_World')
scene.world.color=(0.42,0.42,0.42)
cam=bpy.data.objects.get('CMAI_Calibrated_Side_Camera')
if cam is None:
    data=bpy.data.cameras.new('CMAI_Calibrated_Side_Camera')
    cam=bpy.data.objects.new('CMAI_Calibrated_Side_Camera',data)
    bpy.context.collection.objects.link(cam)
cam.location=(-3.35,0.0,0.42)
cam.data.lens=52.0
cam.data.sensor_width=36.0
cam.rotation_euler=(Vector((0.0,0.0,0.22))-cam.location).to_track_quat('-Z','Y').to_euler()
scene.camera=cam
scene.render.filepath=r'{render.resolve()}'
scene.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=r'{side_blend.resolve()}')
bpy.ops.render.render(write_still=True)
"""
    subprocess.run([args.blender, "--background", "--python-expr", expr], check=True)
    make_side_by_side(args.reference, render, out)
    report = {"reference": str(Path(args.reference).resolve()), "render": str(render.resolve()),
              "side_by_side": str(out.resolve()), "blend": str(side_blend.resolve()),
              "bone_or_mesh_edit": False, "camera": {"location": [-3.35,0.0,0.42], "lens": 52.0}}
    out.with_suffix(".json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
