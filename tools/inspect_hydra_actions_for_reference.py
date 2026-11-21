import bpy, json
from pathlib import Path
blend=r'C:\Users\rober\CreatureMotionAI\data\generated\hydra_two_view_500_pose_pilot\hydra_two_view_march_candidate_5s.blend'
bpy.ops.wm.open_mainfile(filepath=blend)
scene=bpy.context.scene; arm=bpy.data.objects['SevenHeadedHydra_Rig']
ad=arm.animation_data; rows=[]
names=['Root','Body_01','Body_02','Arm.L_01','Arm.L_02','Arm.R_01','Arm.R_02','Leg.L_01','Leg.L_02','Leg.L_03','Leg.R_01','Leg.R_02','Leg.R_03']
for action_name in ['Move','CMAI_Hydra_ReferenceGuided_WalkRoar_5s','CMAI_Hydra_ReferenceExtrema_Timed_5s','CMAI_Hydra_TwoViewMarch_5s']:
    action=bpy.data.actions.get(action_name)
    if not action: continue
    ad.action=action
    if action.slots and hasattr(ad,'action_slot'): ad.action_slot=action.slots[0]
    samples=[]
    end=min(120,int(action.frame_range[1]))
    fs=sorted(set([1,max(1,end//4),max(1,end//2),max(1,3*end//4),end]))
    for f in fs:
        scene.frame_set(f); bpy.context.view_layer.update()
        pb={n:arm.pose.bones[n] for n in names}
        samples.append({'frame':f,'body_z':round((arm.matrix_world@pb['Body_02'].head).z,4),'body_x':round((arm.matrix_world@pb['Body_02'].head).x,4),'body_y':round((arm.matrix_world@pb['Body_02'].head).y,4),'joints':{n:{'head':list((arm.matrix_world@pb[n].head)),'tail':list((arm.matrix_world@pb[n].tail)),'euler':list(pb[n].rotation_euler),'quat':list(pb[n].rotation_quaternion)} for n in names if n!='Root'}})
    rows.append({'action':action_name,'range':list(action.frame_range),'samples':samples})
Path(r'C:\Users\rober\CreatureMotionAI\data\generated\hydra_two_view_500_pose_pilot\action_pose_diagnostic.json').write_text(json.dumps(rows,indent=2))
print('ACTION_POSE_DIAG',json.dumps([{k:r[k] for k in ['action','range']} for r in rows]))
