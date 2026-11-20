import bpy, json, math
from mathutils import Vector

rig=bpy.data.objects.get('CrimsonWingedDragon_Rig')
scene=bpy.context.scene
if rig is None: raise RuntimeError('rig missing')
act=bpy.data.actions.get('FLAP')
rig.animation_data.action=act
if hasattr(rig.animation_data,'action_slot') and act and len(act.slots):
    try: rig.animation_data.action_slot=act.slots[0]
    except Exception: pass
out={'action':'FLAP','frame_data':{},'bones':{}}
for frame in (1,30,60,90,120):
    scene.frame_set(frame); bpy.context.view_layer.update()
    out['frame_data'][str(frame)]={}
    for side in ('L','R'):
      for prefix in ('Leg_Front','Leg_Rear'):
       for n in (1,2,3):
        name=f'{prefix}.{side}_0{n}'
        pb=rig.pose.bones.get(name)
        if pb:
         out['frame_data'][str(frame)][name]={'rot_mode':pb.rotation_mode,'euler':list(pb.rotation_euler),'quat':list(pb.rotation_quaternion),'head':list(rig.matrix_world@pb.head),'tail':list(rig.matrix_world@pb.tail)}
for name in [f'{p}.{s}_0{n}' for p in ('Leg_Front','Leg_Rear') for s in ('L','R') for n in (1,2,3)]:
 b=rig.data.bones.get(name)
 if b:
  out['bones'][name]={'head_local':list(b.head_local),'tail_local':list(b.tail_local),'length':b.length,'matrix_local':[list(row) for row in b.matrix_local]}
print('LEG_POSE_JSON='+json.dumps(out))
