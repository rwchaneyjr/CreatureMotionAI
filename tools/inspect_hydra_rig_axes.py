import bpy

path = r"C:\Users\rober\CreatureMotionAI\data\generated\hydra_two_view_500_pose_pilot\hydra_two_view_march_candidate_5s.blend"
bpy.ops.wm.open_mainfile(filepath=path)
arm = bpy.data.objects["SevenHeadedHydra_Rig"]
for name in ("Root", "Body_01", "Body_02", "Arm.L_01", "Arm.L_02", "Arm.L_03", "Arm.R_01", "Arm.R_02", "Arm.R_03", "Leg.L_01", "Leg.L_02", "Leg.L_03", "Leg.R_01", "Leg.R_02", "Leg.R_03"):
    bone = arm.data.bones[name]
    axes = tuple(tuple(round(value, 3) for value in bone.matrix_local.to_3x3().col[index]) for index in range(3))
    print(name, "parent", bone.parent.name if bone.parent else None,
          "head", tuple(round(value, 3) for value in bone.head_local),
          "tail", tuple(round(value, 3) for value in bone.tail_local),
          "axes", axes)
