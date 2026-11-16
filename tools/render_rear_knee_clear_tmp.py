import bpy, sys
from pathlib import Path
from mathutils import Vector

before, after, out = sys.argv[-3], sys.argv[-2], Path(sys.argv[-1]); out.mkdir(parents=True,exist_ok=True)
names=['Leg_Rear.R_01','Leg_Rear.R_02','Leg_Rear.R_03','Leg_MidRear.R_01','Leg_MidRear.R_02','Leg_MidRear.R_03']
def render(path,label):
    bpy.ops.wm.open_mainfile(filepath=path); s=bpy.context.scene; arm=next(o for o in s.objects if o.type=='ARMATURE'); mesh=next(o for o in s.objects if o.type=='MESH')
    s.frame_set(30); bpy.context.view_layer.update(); pts=[]
    for n in names:
        p=arm.pose.bones[n]; pts += [arm.matrix_world@p.head,arm.matrix_world@p.tail]
    target=sum(pts,Vector())/len(pts)
    camd=bpy.data.cameras.new('CMAI_RearKnee_Clear_Camera'); cam=bpy.data.objects.new('CMAI_RearKnee_Clear_Camera',camd); s.collection.objects.link(cam)
    cam.location=target+Vector((-2.3,0.0,0.25)); camd.type='ORTHO'; camd.ortho_scale=.72; cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler(); s.camera=cam
    arm.show_in_front=True; arm.display_type='WIRE'; arm.data.display_type='BBONE'; mesh.show_transparent=True; mesh.color=(0.2,0.55,0.9,0.55)
    s.render.engine='BLENDER_WORKBENCH'; s.display.shading.color_type='MATERIAL'; s.render.resolution_x=960; s.render.resolution_y=720; s.render.resolution_percentage=100; s.render.image_settings.file_format='PNG'
    for f in (30,70,110):
        s.frame_set(f); bpy.context.view_layer.update(); s.render.filepath=str(out/f'{label}_{f:03d}.png'); bpy.ops.render.render(write_still=True)
render(before,'before'); render(after,'after'); print('done')
