import bpy, sys
from pathlib import Path
from mathutils import Vector

argv=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
def arg(name, default):
    try: return argv[argv.index(name)+1]
    except ValueError: return default
out=Path(arg('--out','data/generated/clean_walk_render')).resolve(); out.mkdir(parents=True,exist_ok=True)
blend_out=arg('--blend-out','')
mp4=arg('--mp4','')
scene=bpy.context.scene
for o in bpy.data.objects:
    if o.get('cmai_proxy') or o.name.startswith(('CMAI_PROXY','CMAI_')):
        o.hide_viewport=True; o.hide_render=True
    if o.type=='ARMATURE':
        o.show_in_front=True; o.display_type='WIRE'
    if o.type=='MESH' and not o.name.startswith('CMAI_'):
        o.hide_viewport=False; o.hide_render=False
mesh=next((o for o in bpy.data.objects if o.type=='MESH' and not o.name.startswith('CMAI_')),None)
if mesh: mesh.hide_viewport=False; mesh.hide_render=False
scene.render.engine='BLENDER_WORKBENCH'; scene.display.shading.light='STUDIO'; scene.display.shading.studio_light='paint.sl'; scene.display.shading.color_type='MATERIAL'; scene.display.shading.show_shadows=True; scene.display.shading.show_cavity=True
scene.render.resolution_x=1280; scene.render.resolution_y=720; scene.render.resolution_percentage=60; scene.render.image_settings.file_format='PNG'
cam=bpy.data.objects.get('CMAI_Clean_Diagnostic_Camera')
if not cam:
    cd=bpy.data.cameras.new('CMAI_Clean_Diagnostic_Camera'); cam=bpy.data.objects.new('CMAI_Clean_Diagnostic_Camera',cd); scene.collection.objects.link(cam)
cam.location=(-3.0,0.0,0.05); target=Vector((0.0,0.0,0.0)); cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler(); cam.data.type='ORTHO'; cam.data.ortho_scale=2.60; scene.camera=cam
action=next((a for a in bpy.data.actions if a.name=='CMAI_Balisk_EightLeg_Walk'),None)
arm=next((o for o in bpy.data.objects if o.type=='ARMATURE'),None)
if arm and action: arm.animation_data_create(); arm.animation_data.action=action
for f in (1,6,12,18,24):
    scene.frame_set(f); scene.render.filepath=str(out/f'frame_{f:02d}.png'); bpy.ops.render.render(write_still=True)
if mp4:
    scene.render.resolution_percentage=60; scene.render.ffmpeg.format='MPEG4'; scene.render.ffmpeg.codec='MPEG4'; scene.render.fps=24; scene.frame_start=1; scene.frame_end=24; scene.render.filepath=str(Path(mp4).resolve()); bpy.ops.render.render(animation=True)
if blend_out:
    bpy.ops.wm.save_as_mainfile(filepath=str(Path(blend_out).resolve()))
print('RENDERED',out)
