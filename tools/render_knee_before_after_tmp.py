import bpy, sys
from pathlib import Path
from mathutils import Vector

BEFORE=sys.argv[-3]; AFTER=sys.argv[-2]; OUT=Path(sys.argv[-1]); OUT.mkdir(parents=True,exist_ok=True)
NAMES=['Leg_Rear.R_01','Leg_Rear.R_02','Leg_Rear.R_03','Leg_MidRear.R_01','Leg_MidRear.R_02','Leg_MidRear.R_03']
def render(blend,label):
    bpy.ops.wm.open_mainfile(filepath=blend); s=bpy.context.scene; arm=next(o for o in s.objects if o.type=='ARMATURE')
    base=s.camera; cam=base.copy(); cam.data=base.data.copy(); cam.name='CMAI_Knee_Closeup'; s.collection.objects.link(cam); s.camera=cam
    for f in (30,70,110):
        s.frame_set(f); bpy.context.view_layer.update(); pts=[]
        for n in NAMES:
            p=arm.pose.bones.get(n)
            if p: pts += [arm.matrix_world@p.head, arm.matrix_world@p.tail]
        c=sum(pts,Vector())/len(pts); cam.data.type='ORTHO'; cam.data.ortho_scale=0.9
        forward=base.rotation_euler.to_matrix()@Vector((0,0,-1)); cam.location=c-forward*2.0
        cam.rotation_euler=(c-cam.location).to_track_quat('-Z','Y').to_euler()
        s.render.filepath=str(OUT/f'{label}_{f:03d}.png'); bpy.ops.render.render(write_still=True)
render(BEFORE,'before'); render(AFTER,'after')
print('rendered')
