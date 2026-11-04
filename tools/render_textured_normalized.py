import argparse, subprocess
from pathlib import Path
def main():
 p=argparse.ArgumentParser(); p.add_argument('--blender',required=True); p.add_argument('--blend',required=True); p.add_argument('--outdir',required=True); a=p.parse_args()
 out=str(Path(a.outdir).resolve()).replace('\\','/')
 expr=f'''import bpy, os
from mathutils import Vector
s=bpy.context.scene; arm=next(o for o in bpy.data.objects if o.type=='ARMATURE')
def look(o,p): o.rotation_euler=(Vector(p)-o.location).to_track_quat('-Z','Y').to_euler()
camd=bpy.data.cameras.new('CMAI_Textured_Side_Camera'); cam=bpy.data.objects.new('CMAI_Textured_Side_Camera',camd); s.collection.objects.link(cam); cam.location=(-2.2,-.35,.15); camd.lens=58; look(cam,(0,-.4,-.05)); s.camera=cam
ld=bpy.data.lights.new('CMAI_Textured_Key','AREA'); lo=bpy.data.objects.new('CMAI_Textured_Key',ld); s.collection.objects.link(lo); lo.location=(-1.5,-2.0,2.5); ld.energy=900; ld.shape='DISK'; ld.size=3; look(lo,(0,-.4,0))
ld2=bpy.data.lights.new('CMAI_Textured_Fill','AREA'); lo2=bpy.data.objects.new('CMAI_Textured_Fill',ld2); s.collection.objects.link(lo2); lo2.location=(1.5,1.0,1.2); ld2.energy=500; ld2.size=2; look(lo2,(0,-.4,0))
s.render.engine='BLENDER_EEVEE'; s.render.resolution_x=960; s.render.resolution_y=540; s.render.resolution_percentage=100; s.render.image_settings.file_format='PNG'; os.makedirs(r'{out}',exist_ok=True)
for f in range(1,25): s.frame_set(f); s.render.filepath=f'{out}/frame_{{f:03d}}.png'; bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=r'{str(Path(a.blend).resolve()).replace(chr(92),chr(47))}')'''
 subprocess.run([a.blender,'--background',a.blend,'--python-expr',expr],check=True)
if __name__=='__main__': main()

