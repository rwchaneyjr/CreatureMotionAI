import bpy
from pathlib import Path

path=r'C:\Users\rober\CreatureMotionAI\data\generated\e2e_balisk_test\builder\seamless\seamless_loop.blend'
out=Path(r'C:\Users\rober\CreatureMotionAI\data\generated\e2e_balisk_test\builder\collision_frames')
out.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=path)
s=bpy.context.scene; s.camera=bpy.data.objects.get('CMAI_Walk_Side') or s.camera
for f in (1,27,28,29,67,68,69,107,108,109):
    s.frame_set(f); s.render.filepath=str(out/f'frame_{f:03d}.png'); bpy.ops.render.render(write_still=True)
