import bpy,json
from pathlib import Path
root=Path(r'C:\Users\rober\CreatureMotionAI');bpy.ops.wm.open_mainfile(filepath=str(root/'data/generated/original_static_standing.blend'));arm=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE');bpy.context.view_layer.update()
def mid(name):
 b=arm.pose.bones[name];return list(arm.matrix_world@((b.head+b.tail)*0.5))
def point(name,tail=False):
 b=arm.pose.bones[name];return list(arm.matrix_world@(b.tail if tail else b.head))
out={'status':'PROVISIONAL_3D_CANDIDATES_REQUIRES_CONFIRMATION','points':{'body_center':mid('Body_02'),'head_snout':point('Head_02',True),'tail_base':point('Tail_01'),'body_length_reference':point('Body_03',False),'ground_contact':point('Leg_Rear.L_03',True)},'source_bones':{'body_center':'Body_02','head_snout':'Head_02.tail','tail_base':'Tail_01.head','body_length_reference':'Body_03.head','ground_contact':'Leg_Rear.L_03.tail'},'note':'These are rig-derived candidates, not confirmed mesh surface correspondences.'}
(root/'data/generated/body_landmark_3d_candidates.json').write_text(json.dumps(out,indent=2))
