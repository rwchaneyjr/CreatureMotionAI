"""Read-only scan of existing dragon Actions for rear legs folded toward tail."""
import bpy, json, math
from mathutils import Vector

rig = bpy.data.objects.get('CrimsonWingedDragon_Rig')
if rig is None:
    raise RuntimeError('dragon armature missing')
scene = bpy.context.scene
rows = {}
for action_name in ('RUN', 'FLAP', 'Move_Scissor_Offset', 'Idle'):
    action = bpy.data.actions.get(action_name)
    if action is None:
        continue
    rig.animation_data_create(); rig.animation_data.action = action
    if getattr(action, 'slots', None) and len(action.slots):
        try: rig.animation_data.action_slot = action.slots[0]
        except Exception: pass
    start, end = map(int, action.frame_range)
    out=[]
    for f in range(start, end+1):
        scene.frame_set(f); bpy.context.view_layer.update()
        head = rig.matrix_world @ rig.pose.bones['Head_02'].tail
        tail = rig.matrix_world @ rig.pose.bones['Tail_06'].tail
        tailward = (tail-head).normalized()
        legs={}
        for side in ('L','R'):
            a=rig.pose.bones[f'Leg_Rear.{side}_01']
            b=rig.pose.bones[f'Leg_Rear.{side}_02']
            c=rig.pose.bones[f'Leg_Rear.{side}_03']
            hip=rig.matrix_world@a.head; knee=rig.matrix_world@b.head
            ankle=rig.matrix_world@c.head; foot=rig.matrix_world@c.tail
            legs[side]={
                'foot_tailward_from_hip': round((foot-hip).dot(tailward),5),
                'knee_tailward_from_hip': round((knee-hip).dot(tailward),5),
                'knee_height_from_hip': round(knee.z-hip.z,5),
                'ankle_height_from_hip': round(ankle.z-hip.z,5),
                'hip_knee_ankle_deg': round(math.degrees((hip-knee).angle(ankle-knee)),2),
                'bone_local_quats': [list(rig.pose.bones[f'Leg_Rear.{side}_{i:02}'].rotation_quaternion) for i in (1,2,3)]
            }
        out.append({'frame':f,'legs':legs})
    rows[action_name]=out
for name, vals in rows.items():
    for side in ('L','R'):
        best=max(vals,key=lambda r:r['legs'][side]['foot_tailward_from_hip'])
        print('CANDIDATE',name,side,json.dumps(best))
    for f in (1, 24, 30, 60, 90, 120):
        found=next((r for r in vals if r['frame']==f),None)
        if found: print('SAMPLE',name,json.dumps(found))
