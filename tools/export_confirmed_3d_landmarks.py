import bpy,json
from pathlib import Path
root=Path(r'C:\Users\rober\CreatureMotionAI');out={}
for o in bpy.data.objects:
 if o.name.startswith('CMAI_Marker_'):
  n=o.get('landmark_name',o.name.replace('CMAI_Marker_',''));out[n]={'world_xyz':list(o.matrix_world.translation),'status':o.get('status','unconfirmed'),'source_bone':o.get('source_bone')}
(root/'data/generated/confirmed_3d_body_landmarks.json').write_text(json.dumps({'status':'USER_CONFIRMED_EXPORT','landmarks':out},indent=2))
print('exported confirmed_3d_body_landmarks.json')
