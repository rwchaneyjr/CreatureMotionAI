import argparse, subprocess
from pathlib import Path
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--blender',required=True); ap.add_argument('--dir',required=True); a=ap.parse_args(); d=Path(a.dir)
    for mode in ('custom','blender_ik','fk'):
        blend=d/f'front_l_{mode}_24f.blend'; out=d/f'{mode}_renders'; out.mkdir(exist_ok=True)
        expr=f'''import bpy
from mathutils import Vector
bpy.ops.wm.open_mainfile(filepath=r"{blend.resolve()}"); s=bpy.context.scene
for o in bpy.data.objects:
    if o.get('cmai_proxy') or o.name.startswith(('CMAI_PROXY','CMAI_')): o.hide_viewport=True; o.hide_render=True
arm=next(o for o in bpy.data.objects if o.type=='ARMATURE'); arm.show_in_front=True; arm.display_type='WIRE'; arm.show_name=False
cam=bpy.data.cameras.new('CMAI_Test_Camera'); co=bpy.data.objects.new('CMAI_Test_Camera',cam); s.collection.objects.link(co); co.location=(-3,0,0.05); co.rotation_euler=(Vector((0,0,0))-co.location).to_track_quat('-Z','Y').to_euler(); cam.type='ORTHO'; cam.ortho_scale=2.6; s.camera=co
s.render.engine='BLENDER_WORKBENCH'; s.render.resolution_x=960; s.render.resolution_y=540; s.render.resolution_percentage=60; s.render.image_settings.file_format='PNG'
for f in (1,6,12,18,24): s.frame_set(f); s.render.filepath=r"{str(out.resolve())}"+('/frame_%02d.png' % f); bpy.ops.render.render(write_still=True)
'''
        subprocess.run([a.blender,'--background','--python-expr',expr],check=True)
if __name__=='__main__': main()
