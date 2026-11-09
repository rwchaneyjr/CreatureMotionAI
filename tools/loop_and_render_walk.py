import bpy, sys
from pathlib import Path
from mathutils import Vector

blend, out_blend, output = sys.argv[sys.argv.index('--') + 1:]
bpy.ops.wm.open_mainfile(filepath=str(Path(blend).resolve()))
s=bpy.context.scene
arm=next(o for o in s.objects if o.type=='ARMATURE')
if not arm.animation_data or not arm.animation_data.action:
    raise RuntimeError('No animation Action found')
action=arm.animation_data.action
for layer in action.layers:
    for strip in layer.strips:
        for bag in strip.channelbags:
            for fc in bag.fcurves:
                if not fc.modifiers:
                    fc.modifiers.new('CYCLES')
s.frame_start=1; s.frame_end=120; s.render.fps=24
cam=bpy.data.objects.get('CMAI_Preview_Side_Camera')
if cam is None:
    bpy.ops.object.camera_add(location=(3.2,0.0,0.62))
    cam=bpy.context.object; cam.name='CMAI_Preview_Side_Camera'
target=Vector((0.0,0.0,0.32)); cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler(); cam.data.type='ORTHO'; cam.data.ortho_scale=2.25; s.camera=cam
if not bpy.data.objects.get('CMAI_Preview_Ground'):
    bpy.ops.mesh.primitive_plane_add(size=20, location=(0,0,-0.20)); bpy.context.object.name='CMAI_Preview_Ground'
s.render.engine='BLENDER_WORKBENCH'; s.render.resolution_x=640; s.render.resolution_y=360; s.render.resolution_percentage=100; s.render.image_settings.file_format='PNG'
out=Path(output).resolve(); seq=out.with_suffix(''); seq.mkdir(parents=True,exist_ok=True); s.render.filepath=str(seq/'frame_')
bpy.ops.wm.save_as_mainfile(filepath=str(Path(out_blend).resolve()))
bpy.ops.render.render(animation=True)
