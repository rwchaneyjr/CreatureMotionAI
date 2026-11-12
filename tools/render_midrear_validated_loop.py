import bpy, sys
from pathlib import Path
args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else sys.argv[1:]
blend, out_dir = args[:2]; out=Path(out_dir); out.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(Path(blend).resolve()))
s=bpy.context.scene; s.render.engine='BLENDER_WORKBENCH'; s.render.resolution_x=960; s.render.resolution_y=540; s.render.resolution_percentage=100; s.render.image_settings.file_format='PNG'; s.render.fps=24
for f in range(1,121):
    s.frame_set(f); s.render.filepath=str(out/f'frame_{f:04d}.png'); bpy.ops.render.render(write_still=True)
print(out)
