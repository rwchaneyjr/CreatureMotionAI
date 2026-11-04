import bpy, json
from pathlib import Path
root=Path(r'C:\Users\rober\CreatureMotionAI')
src=root/'data/generated/body_landmark_confirmation_shifted_candidate.blend'; out=root/'data/generated/body_landmark_confirmation_selected.blend'
bpy.ops.wm.open_mainfile(filepath=str(src))
shift=bpy.data.objects['CMAI_Marker_body_length_shifted'].location.copy()
ref=bpy.data.objects['CMAI_Marker_body_length_reference']; ref.location=shift; ref['status']='confirmed'; ref['confirmation_note']='Selected by user from side-view leg relationship: same height as candidate 3, shifted toward nose behind front pair.'
for n in ('body_center','head_snout','tail_base'):
    o=bpy.data.objects.get('CMAI_Marker_'+n)
    if o: o['status']='confirmed'
bpy.ops.wm.save_as_mainfile(filepath=str(out))
cand=json.loads((root/'data/generated/body_landmark_3d_candidates.json').read_text()); cand['points']['body_length_reference']=list(shift); cand['source_bones']['body_length_reference']='user_selected_shifted_mesh_candidate'; cand['status']='FOUR_BODY_REFERENCES_SELECTED_GROUND_EXCLUDED'; cand['note']='Ground contact remains excluded.'
(root/'data/generated/body_landmark_3d_selected.json').write_text(json.dumps(cand,indent=2))
