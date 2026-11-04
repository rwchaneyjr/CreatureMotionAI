import bpy,json
from pathlib import Path
root=Path(r'C:\Users\rober\CreatureMotionAI'); src=root/'data/generated/original_static_standing.blend'; out=root/'data/generated/body_landmark_confirmation.blend'; data=json.loads((root/'data/generated/body_landmark_3d_candidates.json').read_text())
bpy.ops.wm.open_mainfile(filepath=str(src));s=bpy.context.scene; arm=next(o for o in s.objects if o.type=='ARMATURE'); arm.show_in_front=True; arm.display_type='WIRE'
colors={'body_center':(1,0.1,0.1,1),'head_snout':(0.1,1,0.1,1),'tail_base':(0.1,0.4,1,1),'body_length_reference':(1,0.6,0.05,1),'ground_contact':(1,0.1,1,1)}
labels={'body_center':'BODY CENTER','head_snout':'SNOUT','tail_base':'TAIL BASE','body_length_reference':'BODY-LENGTH REFERENCE','ground_contact':'GROUND CONTACT'}
for name,pos in data['points'].items():
 o=bpy.data.objects.get('CMAI_Marker_'+name) or bpy.data.objects.new('CMAI_Marker_'+name,None); 
 if not o.users_scene:s.collection.objects.link(o)
 o.location=pos;o.empty_display_type='SPHERE';o.empty_display_size=.035;o.color=colors[name];o.show_name=True;o.name='CMAI_Marker_'+name;o['landmark_name']=name;o['status']='unconfirmed';o['source_bone']=data['source_bones'][name]
 txt=bpy.data.curves.new('CMAI_Label_'+name,'FONT');txt.body=labels[name];txt.size=.035;txt.align_x='CENTER';to=bpy.data.objects.new('CMAI_Label_'+name,txt);s.collection.objects.link(to);to.location=(pos[0],pos[1],pos[2]+.05);to.color=colors[name]
s['CMAI_INSTRUCTIONS']='Select CMAI_Marker_* empties and press G to move. Enable Snap To Face (Shift+Tab) for mesh snapping. Set marker custom property status to confirmed or adjusted. Run export_confirmed_3d_landmarks.py after confirmation.'
bpy.ops.wm.save_as_mainfile(filepath=str(out))
