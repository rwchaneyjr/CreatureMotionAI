"""Render a lightweight five-second preview of a generated walk."""
import argparse, bpy, sys
from mathutils import Vector
from pathlib import Path

def main():
    p=argparse.ArgumentParser(); p.add_argument('--blend',required=True); p.add_argument('--output',required=True); p.add_argument('--end-frame',type=int,default=120); p.add_argument('--ground-plane',action='store_true'); p.add_argument('--side-view',action='store_true'); p.add_argument('--side-view-opposite',action='store_true'); p.add_argument('--closeup',action='store_true'); p.add_argument('--width',type=int,default=640); p.add_argument('--height',type=int,default=360)
    argv=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else sys.argv[1:]; a=p.parse_args(argv)
    bpy.ops.wm.open_mainfile(filepath=str(Path(a.blend).resolve()))
    s=bpy.context.scene; s.frame_start=1; s.frame_end=a.end_frame; s.render.fps=24
    cam=next((o for o in s.objects if o.type=='CAMERA'),None)
    if a.side_view:
        # The Balisk's length is along local Y.  A temporary camera on +X
        # exposes the complete side and the Front.L/Rear.L leg motion.
        cam=bpy.data.objects.get('CMAI_Preview_Side_Camera')
        if cam is None:
            side_x = -3.2 if a.side_view_opposite else 3.2
            bpy.ops.object.camera_add(location=(side_x, 0.0, 0.62))
            cam=bpy.context.object; cam.name='CMAI_Preview_Side_Camera'
        target=Vector((0.0, 0.0, 0.12 if a.closeup else 0.32))
        direction=target-cam.location
        cam.rotation_euler=direction.to_track_quat('-Z','Y').to_euler()
        cam.data.type='ORTHO'; cam.data.ortho_scale=1.35 if a.closeup else 2.25
        s.camera=cam
    if cam: s.camera=cam
    if a.ground_plane and not bpy.data.objects.get('CMAI_Preview_Ground'):
        bpy.ops.mesh.primitive_plane_add(size=20, location=(0,0,-0.20))
        ground=bpy.context.object; ground.name='CMAI_Preview_Ground'; ground.hide_render=False
    s.render.engine='BLENDER_WORKBENCH'
    s.render.resolution_x=a.width; s.render.resolution_y=a.height; s.render.resolution_percentage=100
    out=Path(a.output).resolve(); seq=out.with_suffix('')
    s.render.image_settings.file_format='PNG'; s.render.filepath=str(seq / 'frame_')
    seq.mkdir(parents=True, exist_ok=True)
    bpy.ops.render.render(animation=True)
if __name__=='__main__': main()
