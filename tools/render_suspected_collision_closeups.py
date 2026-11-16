import bpy
from pathlib import Path
from mathutils import Vector

blend=r'C:\Users\rober\CreatureMotionAI\data\generated\e2e_balisk_test\builder\seamless\seamless_loop.blend'
out=Path(r'C:\Users\rober\CreatureMotionAI\data\generated\e2e_balisk_test\builder\suspected_collision\frames'); out.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=blend); s=bpy.context.scene
arm=next(o for o in s.objects if o.type=='ARMATURE');
names=['Leg_Rear.R_01','Leg_Rear.R_02','Leg_Rear.R_03','Leg_MidRear.R_01','Leg_MidRear.R_02','Leg_MidRear.R_03']
def center():
    pts=[]
    for n in names:
        p=arm.pose.bones[n]; pts.extend([arm.matrix_world@p.head,arm.matrix_world@p.tail])
    return sum(pts,Vector())/len(pts)
base=s.camera
forward=base.rotation_euler.to_matrix() @ Vector((0,0,-1))
distance=3.0
cam=base.copy(); cam.data=base.data.copy(); cam.name='CMAI_Temp_Collision_Closeup'; s.collection.objects.link(cam); s.camera=cam
for f in (1,28,68,108):
    s.frame_set(f); bpy.context.view_layer.update(); c=center(); cam.data.type='ORTHO'; cam.data.ortho_scale=1.8
    # Preserve the validated side-view direction, only retarget framing.
    cam.location=c-forward*distance
    cam.rotation_euler=(c-cam.location).to_track_quat('-Z','Y').to_euler()
    s.render.filepath=str(out/f'collision_frame_{f:03d}.png'); bpy.ops.render.render(write_still=True)
