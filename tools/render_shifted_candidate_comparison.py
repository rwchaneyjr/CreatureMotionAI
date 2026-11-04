import bpy
from pathlib import Path
from mathutils import Vector
root=Path(r'C:\Users\rober\CreatureMotionAI')
bpy.ops.wm.open_mainfile(filepath=str(root/'data/generated/body_landmark_confirmation_shifted_candidate.blend'))
scene=bpy.context.scene; mesh=next(o for o in scene.objects if o.type=='MESH'); marker=bpy.data.objects.get('CMAI_Marker_body_length_shifted')
allp=[mesh.matrix_world@Vector(c) for c in mesh.bound_box]; mn=Vector((min(p.x for p in allp),min(p.y for p in allp),min(p.z for p in allp))); mx=Vector((max(p.x for p in allp),max(p.y for p in allp),max(p.z for p in allp))); center=(mn+mx)*.5
bpy.ops.mesh.primitive_uv_sphere_add(segments=20, ring_count=10, radius=.055, location=Vector((mn.x-.08, marker.location.y, marker.location.z))); s=bpy.context.object; mat=bpy.data.materials.new('CMAI_SHIFTED_MAGENTA'); mat.diffuse_color=(1,0,1,1); s.data.materials.append(mat)
camd=bpy.data.cameras.new('CMAI_Shifted_Camera'); cam=bpy.data.objects.new('CMAI_Shifted_Camera',camd); scene.collection.objects.link(cam); cam.location=(mn.x-(mx.x-mn.x)*2.5,center.y,center.z); cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler(); camd.type='ORTHO'; camd.ortho_scale=max(1,(mx.z-mn.z)*1.25); scene.camera=cam
scene.render.engine='BLENDER_WORKBENCH'; scene.render.resolution_x=640; scene.render.resolution_y=720; scene.render.resolution_percentage=100; scene.render.filepath=str(root/'data/generated/body_length_shifted_model.png'); scene.display.shading.light='STUDIO'; scene.display.shading.color_type='MATERIAL'; scene.display.shading.show_shadows=True; scene.display.shading.show_cavity=True; bpy.ops.render.render(write_still=True)
