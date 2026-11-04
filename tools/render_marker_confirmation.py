import bpy
from mathutils import Vector
from pathlib import Path

root = Path(r'C:\Users\rober\CreatureMotionAI')
scene = bpy.context.scene
arm = next((o for o in scene.objects if o.type == 'ARMATURE'), None)
meshes = [o for o in scene.objects if o.type == 'MESH']
if not meshes:
    raise RuntimeError('No mesh found')
allpts = [arm.matrix_world @ Vector(c) for o in meshes for c in o.bound_box]
mn = Vector((min(v.x for v in allpts), min(v.y for v in allpts), min(v.z for v in allpts)))
mx = Vector((max(v.x for v in allpts), max(v.y for v in allpts), max(v.z for v in allpts)))
center = (mn + mx) * 0.5
pts = [o for o in scene.objects if o.name.startswith('CMAI_Marker_')]
for p in pts:
    bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=8, radius=0.045, location=p.location)
    s = bpy.context.object
    s.name = 'CMAI_Preview_' + p.name
    mat = bpy.data.materials.new(s.name + '_MAT'); mat.diffuse_color = (*p.color[:3], 1.0)
    s.data.materials.append(mat)
    # Side-view callout marker: placed just in front of the mesh for visibility.
    callout = p.location.copy(); callout.x = mn.x - 0.08
    bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=8, radius=0.055, location=callout)
    cs = bpy.context.object; cs.name = 'CMAI_Callout_' + p.name
    cm = bpy.data.materials.new(cs.name + '_MAT'); cm.diffuse_color = (*p.color[:3], 1.0); cs.data.materials.append(cm)
    curve = bpy.data.curves.new('CMAI_CalloutLine_'+p.name, 'CURVE'); curve.dimensions='3D'; curve.bevel_depth=0.006
    spline = curve.splines.new('POLY'); spline.points.add(1)
    spline.points[0].co = (*p.location, 1); spline.points[1].co = (*callout, 1)
    lo = bpy.data.objects.new('CMAI_CalloutLine_'+p.name, curve); scene.collection.objects.link(lo)
    tx = bpy.data.curves.new('CMAI_CalloutText_'+p.name, 'FONT'); tx.body = p.get('landmark_name', p.name); tx.size = 0.05; tx.align_x='LEFT'
    to = bpy.data.objects.new('CMAI_CalloutText_'+p.name, tx); scene.collection.objects.link(to)
    to.location = (callout.x - 0.01, callout.y, callout.z + 0.07)
    to.rotation_euler = (0.0, -1.5707963, 0.0); to.data.materials.append(cm)
cam = bpy.data.objects.get('CMAI_Confirmation_Camera') or bpy.data.cameras.new('CMAI_Confirmation_Camera')
co = bpy.data.objects.get('CMAI_Confirmation_Camera') or bpy.data.objects.new('CMAI_Confirmation_Camera', cam.data if hasattr(cam,'data') else cam)
if co.name not in scene.objects: scene.collection.objects.link(co)
co.location = (mn.x - max(2.0, (mx.x-mn.x)*2.5), center.y, center.z)
co.rotation_euler = (center - co.location).to_track_quat('-Z', 'Y').to_euler()
cam = co.data
cam.type='ORTHO'; cam.ortho_scale=max(1.0,(mx.z-mn.z)*1.35); scene.camera=co
scene.render.engine='BLENDER_WORKBENCH'; scene.render.resolution_x=1000; scene.render.resolution_y=700; scene.render.resolution_percentage=100
scene.render.filepath=str(root/'data/generated/body_landmark_confirmation_preview.png')
scene.display.shading.light='STUDIO'; scene.display.shading.color_type='MATERIAL'; scene.display.shading.show_shadows=True; scene.display.shading.show_cavity=True
bpy.ops.render.render(write_still=True)
