"""Assemble paired PNG camera renders into a 1280x720 MP4 using Blender FFmpeg."""
import argparse, subprocess
from pathlib import Path


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--render-dir", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--blender", required=True)
    p.add_argument("--frames", type=int, default=240)
    a = p.parse_args()
    root = Path(a.render_dir).resolve()
    out = Path(a.output).resolve()
    expr = f"""
import bpy
bpy.ops.wm.read_factory_settings(use_empty=True)
s=bpy.context.scene
s.sequence_editor_create()
s.render.resolution_x=1280; s.render.resolution_y=720; s.render.resolution_percentage=100
s.render.image_settings.file_format='FFMPEG'
s.render.fps=24; s.frame_start=1; s.frame_end={a.frames}
s.render.ffmpeg.format='MPEG4'; s.render.ffmpeg.codec='MPEG4'; s.render.ffmpeg.constant_rate_factor='MEDIUM'; s.render.filepath=r'{out}'
for channel,label,offset in [(1,'side',-320),(2,'front',320)]:
    first=r'{(root/'side'/'frame_0001.png').as_posix()}'
    strip=s.sequence_editor.strips.new_image(label,first,channel,1)
    for f in range(2,{a.frames}+1): strip.elements.append(f'frame_{{f:04d}}.png')
    strip.frame_final_duration={a.frames}; strip.transform.scale_x=2.0; strip.transform.scale_y=2.0; strip.transform.offset_x=offset
bpy.ops.render.render(animation=True)
print('ASSEMBLED',r'{out}')
"""
    subprocess.run([a.blender, "--background", "--python-expr", expr], check=True)
    print({"output": str(out), "frames": a.frames})


if __name__ == "__main__":
    main()
