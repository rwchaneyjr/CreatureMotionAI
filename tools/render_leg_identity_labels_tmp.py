import bpy
from pathlib import Path
from mathutils import Vector

src=r'C:\Users\rober\CreatureMotionAI\data\generated\e2e_balisk_test\builder\seamless\seamless_loop.blend'
out=Path(r'C:\Users\rober\CreatureMotionAI\data\generated\e2e_balisk_test\builder\bending_diagnosis\identity_labels'); out.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=src); s=bpy.context.scene; arm=next(o for o in s.objects if o.type=='ARMATURE'); s.camera=bpy.data.objects.get('CMAI_Walk_Side') or s.camera
col=bpy.data.collections.new('CMAI_Temporary_Leg_Identity_Labels'); s.collection.children.link(col)
colors={'Front.L':(1,0.1,0.1,1),'Front.R':(1,0.5,0.1,1),'MidFront.L':(0.2,1,0.2,1),'MidFront.R':(0.1,0.8,0.5,1),'MidRear.L':(0.1,0.6,1,1),'MidRear.R':(0.2,0.2,1,1),'Rear.L':(0.7,0.2,1,1),'Rear.R':(1,0.1,0.8,1)}
for leg,color in colors.items():
    mat=bpy.data.materials.new('CMAI_LABEL_'+leg.replace('.','_')); mat.diffuse_color=color; mat.metallic=.1; mat.roughness=.3
    points=[]
    for i in (1,2,3):
        p=arm.pose.bones[f'Leg_{leg}_{i:02d}']; points += [arm.matrix_world@p.head] if i<3 else [arm.matrix_world@p.head,arm.matrix_world@p.tail]
    for j,pt in enumerate(points):
        bpy.ops.mesh.primitive_uv_sphere_add(segments=12, ring_count=6, radius=.018, location=pt)
        o=bpy.context.object; o.name=f'CMAI_LABEL_{leg}_{j}'; o.data.materials.append(mat)
        for c in list(o.users_collection): c.objects.unlink(o)
        col.objects.link(o)
    # A short colored line over the chain using thin cylinders.
    for a,b in zip(points[:-1],points[1:]):
        d=b-a; mid=(a+b)*.5
        bpy.ops.mesh.primitive_cylinder_add(vertices=8, radius=.006, depth=d.length, location=mid)
        o=bpy.context.object; o.name=f'CMAI_LABEL_LINE_{leg}'; o.data.materials.append(mat); o.rotation_mode='QUATERNION'; o.rotation_quaternion=d.to_track_quat('Z','Y')
        for c in list(o.users_collection): c.objects.unlink(o)
        col.objects.link(o)
    # Label text near the hip, facing the camera.
    p=points[0]; bpy.ops.object.text_add(location=p+Vector((0,0,.04)))
    t=bpy.context.object; t.name=f'CMAI_LABEL_TEXT_{leg}'; t.data.body=leg; t.data.size=.045; t.data.extrude=.001; t.data.materials.append(mat)
    t.rotation_euler=s.camera.rotation_euler
    for c in list(t.users_collection): c.objects.unlink(t)
    col.objects.link(t)
s.render.resolution_x=1280; s.render.resolution_y=720; s.render.resolution_percentage=100
for f in (1,28):
    s.frame_set(f); s.render.filepath=str(out/f'leg_identity_frame_{f:03d}.png'); bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=str(out/'leg_identity_labeled.blend'),copy=True)
