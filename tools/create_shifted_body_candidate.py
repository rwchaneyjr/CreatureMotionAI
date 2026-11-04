import bpy, json
from pathlib import Path
from mathutils import Vector
root=Path(r'C:\Users\rober\CreatureMotionAI')
src=root/'data/generated/body_landmark_confirmation.blend'; out=root/'data/generated/body_landmark_confirmation_shifted_candidate.blend'
bpy.ops.wm.open_mainfile(filepath=str(src)); scene=bpy.context.scene; mesh=next(o for o in scene.objects if o.type=='MESH'); arm=next(o for o in scene.objects if o.type=='ARMATURE')
body3=arm.data.bones.get('Body_03'); target=arm.matrix_world@body3.tail_local; desired=Vector((target.x,target.y-0.055,target.z))
best=None
for v in mesh.data.vertices:
    p=mesh.matrix_world@v.co; d=((p.y-desired.y)**2+(p.z-desired.z)**2+(p.x-desired.x)**2*0.25)
    if best is None or d<best[0]: best=(d,p,v.index)
_,p,idx=best
o=bpy.data.objects.get('CMAI_Marker_body_length_shifted') or bpy.data.objects.new('CMAI_Marker_body_length_shifted',None); scene.collection.objects.link(o) if not o.users_scene else None; o.location=p; o.empty_display_type='SPHERE'; o.empty_display_size=.035; o.color=(0.1,0.8,1,1); o.show_name=True; o['landmark_name']='body_length_shifted_toward_nose'; o['status']='unconfirmed'; o['source_vertex']=idx; o['source_bone']='Body_03.tail shifted toward nose'
scene['CMAI_SHIFTED_CANDIDATE_NOTE']='Same approximate height as Body_03.tail, shifted toward nose and snapped to nearest torso mesh vertex. Unconfirmed.'
bpy.ops.wm.save_as_mainfile(filepath=str(out)); (root/'data/generated/body_length_shifted_candidate.json').write_text(json.dumps({'status':'unconfirmed','world_xyz':list(p),'source_vertex':idx,'source':'Body_03.tail height shifted toward nose'},indent=2))
