import bpy
import sys
from pathlib import Path
from mathutils import Vector

blend, frame1_path, frame12_path, pair_path = sys.argv[sys.argv.index('--') + 1:]
bpy.ops.wm.open_mainfile(filepath=str(Path(blend).resolve()))
scene = bpy.context.scene
out1 = Path(frame1_path).resolve()
out12 = Path(frame12_path).resolve()
pair = Path(pair_path).resolve()
out1.parent.mkdir(parents=True, exist_ok=True)

cam = bpy.data.objects.get('CMAI_FrontL_Comparison_Camera')
if cam is None:
    cam_data = bpy.data.cameras.new('CMAI_FrontL_Comparison_Camera')
    cam = bpy.data.objects.new('CMAI_FrontL_Comparison_Camera', cam_data)
    scene.collection.objects.link(cam)
cam.location = (3.2, -0.82, 0.38)
target = Vector((0.0, -0.82, -0.12))
cam.rotation_euler = (target - cam.location).to_track_quat('-Z', 'Y').to_euler()
cam.data.type = 'ORTHO'
cam.data.ortho_scale = 0.72
scene.camera = cam
scene.render.engine = 'BLENDER_WORKBENCH'
scene.render.resolution_x = 960
scene.render.resolution_y = 540
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
scene.render.film_transparent = False

def render(frame, path):
    scene.frame_set(frame)
    bpy.context.view_layer.update()
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)

render(1, out1)
render(12, out12)

i1 = bpy.data.images.load(str(out1), check_existing=False)
i2 = bpy.data.images.load(str(out12), check_existing=False)
w, h = i1.size[:]
assert i2.size[:] == (w, h)
p1 = list(i1.pixels[:])
p2 = list(i2.pixels[:])
joined = [0.0] * (w * 2 * h * 4)
for y in range(h):
    for x in range(w):
        s = (y * w + x) * 4
        d1 = (y * (w * 2) + x) * 4
        d2 = (y * (w * 2) + x + w) * 4
        joined[d1:d1+4] = p1[s:s+4]
        joined[d2:d2+4] = p2[s:s+4]
canvas = bpy.data.images.new('CMAI_FrontL_Frame1_vs_Frame12', width=w * 2, height=h, alpha=True)
canvas.pixels = joined
canvas.filepath_raw = str(pair)
canvas.file_format = 'PNG'
canvas.save()
print(f'RENDERED {out1} {out12} {pair}')
