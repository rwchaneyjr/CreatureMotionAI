import argparse, subprocess
from pathlib import Path
def main():
 p=argparse.ArgumentParser(); p.add_argument('--blender',required=True); p.add_argument('--blend',required=True); p.add_argument('--outdir',required=True); a=p.parse_args()
 out=str(Path(a.outdir).resolve()).replace('\\','/')
 expr=f'''import bpy, math
from mathutils import Vector
s=bpy.context.scene; arm=next(o for o in bpy.data.objects if o.type=='ARMATURE'); mesh=next(o for o in bpy.data.objects if o.type=='MESH')
def look(obj,pt): obj.rotation_euler=(Vector(pt)-obj.location).to_track_quat('-Z','Y').to_euler()
for o in list(bpy.data.objects):
 if o.name.startswith('CMAI_Render_'): bpy.data.objects.remove(o,do_unlink=True)
floor=bpy.data.objects.new('CMAI_Render_Ground',bpy.data.meshes.new('CMAI_Render_GroundMesh')); s.collection.objects.link(floor); floor.location=(0,0,-0.245); bpy.context.view_layer.objects.active=floor; floor.select_set(True); bpy.ops.object.modifier_add(type='SOLIDIFY'); floor.select_set(False)
camd=bpy.data.cameras.new('CMAI_Render_Side_Data'); cam=bpy.data.objects.new('CMAI_Render_Side',camd); s.collection.objects.link(cam); cam.location=(-2.2,-0.35,0.15); camd.lens=58; look(cam,(0,-0.4,-0.05)); s.camera=cam
s.render.engine='BLENDER_WORKBENCH'; s.display.shading.light='STUDIO'; s.display.shading.studio_light='paint.sl'; s.display.shading.color_type='MATERIAL'; s.render.resolution_x=960; s.render.resolution_y=540; s.render.resolution_percentage=100; s.render.image_settings.file_format='PNG'; s.render.fps=24
Path=r'{out}'; import os; os.makedirs(Path,exist_ok=True)
for f in range(1,25): s.frame_set(f); s.render.filepath=f'{{Path}}/frame_{{f:03d}}.png'; bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=r'{str(Path(a.blend).resolve()).replace(chr(92),chr(47))}')
'''
 subprocess.run([a.blender,'--background',a.blend,'--python-expr',expr],check=True)
if __name__=='__main__': main()
