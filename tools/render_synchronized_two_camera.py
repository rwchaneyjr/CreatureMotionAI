"""Render one Blender Action from two fixed cameras and build a synchronized split MP4."""
import argparse, json, subprocess
from pathlib import Path


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--blend", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--report", required=True)
    p.add_argument("--render-dir", required=True)
    p.add_argument("--blender", required=True)
    p.add_argument("--frames", type=int, default=240)
    a = p.parse_args()
    root = Path(a.render_dir).resolve()
    side = root / "side"
    front = root / "front"
    side.mkdir(parents=True, exist_ok=True)
    front.mkdir(parents=True, exist_ok=True)
    expr = f"""
import bpy, json
from mathutils import Vector
bpy.ops.wm.open_mainfile(filepath=r'{Path(a.blend).resolve()}')
s=bpy.context.scene
rig=next((o for o in s.objects if o.type=='ARMATURE'),None)
if rig is None: raise RuntimeError('No original armature found')
if len(rig.data.bones) != 38: raise RuntimeError('Expected original 38-bone armature')
s.render.engine='BLENDER_WORKBENCH'
s.render.resolution_x=640; s.render.resolution_y=360; s.render.resolution_percentage=100
s.render.image_settings.file_format='PNG'
s.render.fps=24
s.frame_start=1; s.frame_end={a.frames}
target=rig.matrix_world.translation.copy()
def camera(name, location):
    c=bpy.data.objects.get(name)
    if c is None:
        d=bpy.data.cameras.new(name); c=bpy.data.objects.new(name,d); s.collection.objects.link(c)
    c.location=location; c.data.lens=52; c.data.sensor_width=36
    c.rotation_euler=(target-c.location).to_track_quat('-Z','Y').to_euler()
    return c
cam_a=camera('CMAI_Synchronized_Side_Camera',target+Vector((-3.35,0,0.40)))
cam_b=camera('CMAI_Synchronized_Front_Camera',target+Vector((0,-3.35,0.40)))
metadata={{'fps':24,'frames':{a.frames},'resolution':[1280,720],'source_blend':r'{Path(a.blend).resolve()}', 'armature':rig.name, 'bone_count':len(rig.data.bones), 'cameras':{{'A_side':cam_a.name,'B_front':cam_b.name}},'frame_pairs':[]}}
for f in range(1,{a.frames}+1):
    s.frame_set(f)
    for label,cam,outdir in [('A_side',cam_a,r'{side.as_posix()}'),('B_front',cam_b,r'{front.as_posix()}')]:
        s.camera=cam; s.render.filepath=outdir+f'/frame_{{f:04d}}.png'; bpy.ops.render.render(write_still=True)
    metadata['frame_pairs'].append({{'frame':f,'side':f'frame_{{f:04d}}.png','front':f'frame_{{f:04d}}.png'}})
open(r'{Path(a.report).resolve()}','w',encoding='utf-8').write(json.dumps(metadata,indent=2))
bpy.ops.wm.save_as_mainfile(filepath=r'{Path(a.output).resolve()}')
print(json.dumps({{'frames':{a.frames},'bone_count':len(rig.data.bones),'output':r'{Path(a.output).resolve()}'}}))
"""
    subprocess.run([a.blender, "--background", "--python-expr", expr], check=True)
    print(json.dumps({"render_dir": str(root), "frames": a.frames}))


if __name__ == "__main__":
    main()
