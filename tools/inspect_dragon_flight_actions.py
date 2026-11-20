"""Read-only summary of dragon Actions for a tucked-leg flight pose."""
import json
import math
import bpy
from mathutils import Vector

arm = bpy.data.objects.get("CrimsonWingedDragon_Rig") or next(
    (obj for obj in bpy.data.objects if obj.type == 'ARMATURE'), None)
if arm is None:
    raise RuntimeError("Dragon armature not found")
scene = bpy.context.scene
previous_frame = scene.frame_current
previous_action = arm.animation_data.action if arm.animation_data else None
previous_slot = getattr(arm.animation_data, "action_slot", None) if arm.animation_data else None
chains = {
    "Front.L": ["Leg_Front.L_01", "Leg_Front.L_02", "Leg_Front.L_03"],
    "Front.R": ["Leg_Front.R_01", "Leg_Front.R_02", "Leg_Front.R_03"],
    "Rear.L": ["Leg_Rear.L_01", "Leg_Rear.L_02", "Leg_Rear.L_03"],
    "Rear.R": ["Leg_Rear.R_01", "Leg_Rear.R_02", "Leg_Rear.R_03"],
}
summary = {}
try:
    if arm.animation_data is None:
        arm.animation_data_create()
    for name in ("Move_Scissor_Offset", "FLAP", "RUN", "Idle", "Attack", "Death"):
        action = bpy.data.actions.get(name)
        if action is None:
            continue
        arm.animation_data.action = action
        slots = getattr(action, "slots", None)
        if slots and len(slots):
            try:
                arm.animation_data.action_slot = next((s for s in slots if s.target_id_type == 'OBJECT'), slots[0])
            except (AttributeError, TypeError):
                pass
        start, end = map(int, action.frame_range)
        frame_samples = sorted(set([start, (start + end)//2, end]))
        rows=[]
        for frame in frame_samples:
            scene.frame_set(frame)
            bpy.context.view_layer.update()
            body = arm.matrix_world @ arm.pose.bones["Body_01"].head
            legs={}
            for leg, chain in chains.items():
                pb=[arm.pose.bones[b] for b in chain]
                hip=arm.matrix_world @ pb[0].head
                knee=arm.matrix_world @ pb[1].head
                foot=arm.matrix_world @ pb[2].tail
                v1=(hip-knee).normalized(); v2=(foot-knee).normalized()
                flex=math.degrees(v1.angle(v2))
                legs[leg]={"hip_knee_foot_angle_deg":round(flex,2),
                           "foot_to_body_distance":round((foot-body).length,4),
                           "knee_body_distance":round((knee-body).length,4),
                           "foot_world_z":round(foot.z,4)}
            wing_motion=[]
            for bn in ("Wing.L_01","Wing.R_01"):
                q=arm.pose.bones[bn].matrix.to_quaternion()
                wing_motion.append([round(float(x),4) for x in q])
            rows.append({"frame":frame,"legs":legs,"wing_quaternions":wing_motion})
        summary[name]={"frame_range":list(action.frame_range),"samples":rows}
finally:
    if arm.animation_data:
        arm.animation_data.action=previous_action
        if previous_slot is not None:
            try: arm.animation_data.action_slot=previous_slot
            except (AttributeError,TypeError): pass
    scene.frame_set(previous_frame)
print("DRAGON_FLIGHT_ACTION_SUMMARY "+json.dumps(summary))
