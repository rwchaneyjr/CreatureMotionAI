"""Build a synchronized two-camera Blender studio from the clean standing pose."""
import argparse, json, subprocess
from pathlib import Path

def main():
    p=argparse.ArgumentParser(); p.add_argument('--blend',required=True); p.add_argument('--output',required=True); p.add_argument('--report',required=True); p.add_argument('--render-dir',required=True); p.add_argument('--blender',required=True); a=p.parse_args()
    out=Path(a.output); render_dir=Path(a.render_dir); render_dir.mkdir(parents=True,exist_ok=True); out.parent.mkdir(parents=True,exist_ok=True)
    expr=f"""
import bpy, json
from mathutils import Vector
bpy.ops.wm.open_mainfile(filepath=r'{Path(a.blend).resolve()}')
s=bpy.context.scene; s.frame_start=1; s.frame_end=1; s.render.resolution_x=640; s.render.resolution_y=360; s.render.resolution_percentage=100; s.render.image_settings.file_format='PNG'
if s.world is None: s.world=bpy.data.worlds.new('CMAI_TwoCamera_World')
s.world.color=(0.42,0.42,0.42)
target=Vector((0,0,0.16))
def make(name,loc,lens=52.0):
    old=bpy.data.objects.get(name)
    if old: bpy.data.objects.remove(old,do_unlink=True)
    d=bpy.data.cameras.new(name); c=bpy.data.objects.new(name,d); bpy.context.collection.objects.link(c); c.location=loc; d.lens=lens; d.sensor_width=36.0; c.rotation_euler=(target-c.location).to_track_quat('-Z','Y').to_euler(); return c
side=make('CMAI_Studio_Camera_A_Side',(-3.35,0,0.40)); front=make('CMAI_Studio_Camera_B_Front',(0,-4.10,0.40))
def matrix(o):
    m=o.matrix_world if hasattr(o,'matrix_world') else o
    return [[round(float(v),9) for v in row] for row in m]
cal={{'resolution':[640,360],'frame':1,'target':list(target),'cameras':{{}}}}
for label,c in [('A_side',side),('B_front',front)]:
    s.camera=c; s.render.filepath=r'{render_dir.resolve().as_posix()}/'+label+'.png'; bpy.ops.render.render(write_still=True)
    cal['cameras'][label]={{'object':c.name,'location':list(c.location),'rotation_euler':list(c.rotation_euler),'lens':c.data.lens,'sensor_width':c.data.sensor_width,'matrix_world':matrix(c),'projection_matrix':matrix(c.calc_matrix_camera(bpy.context.evaluated_depsgraph_get(),x=640,y=360))}}
s.camera=side; bpy.ops.wm.save_as_mainfile(filepath=r'{out.resolve()}')
open(r'{Path(a.report).resolve()}','w',encoding='utf-8').write(json.dumps(cal,indent=2))
print(json.dumps(cal))
"""
    r=subprocess.run([a.blender,'--background','--python-expr',expr],capture_output=True,text=True,check=True)
    print(r.stdout[-4000:]); print(r.stderr[-4000:])
if __name__=='__main__': main()
