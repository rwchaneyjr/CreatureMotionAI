import bpy, math
from pathlib import Path
from mathutils import Vector
root=Path(r'C:\Users\rober\CreatureMotionAI')
bpy.ops.wm.open_mainfile(filepath=str(root/'data/generated/original_static_standing.blend'))
scene=bpy.context.scene; arm=next(o for o in scene.objects if o.type=='ARMATURE'); mesh=next(o for o in scene.objects if o.type=='MESH')
allp=[mesh.matrix_world@Vector(c) for c in mesh.bound_box]; mn=Vector((min(p.x for p in allp),min(p.y for p in allp),min(p.z for p in allp))); mx=Vector((max(p.x for p in allp),max(p.y for p in allp),max(p.z for p in allp)))
names=[('Body_02.tail','Body_02 tail',(1,0.1,0.1,1)),('Body_03.head','Body_03 head',(1,0.55,0.05,1)),('Body_03.tail','Body_03 tail',(1,0.9,0.05,1)),('Head_01.head','Head_01 head',(0.1,1,0.1,1)),('Body_03.mid','Body_03 midpoint',(0.1,0.7,1,1))]
poses={b.name:arm.matrix_world@b.head_local for b in arm.data.bones}|{b.name+'.tail':arm.matrix_world@b.tail_local for b in arm.data.bones}
proj=[]
for key,label,col in names:
    if key=='Body_03.mid': p=(poses['Body_03']+poses['Body_03.tail'])*.5
    elif key.endswith('.head'): p=poses[key[:-5]]
    else: p=poses[key]
    proj.append({'label':label,'y':p.y,'z':p.z,'color':col[:3]})
    shown=p.copy(); shown.x=mn.x-0.08 if 'mn' in globals() else p.x
    bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=8, radius=.035, location=shown)
    o=bpy.context.object; o.name='CANDIDATE_'+label.replace(' ','_'); m=bpy.data.materials.new(o.name+'MAT'); m.diffuse_color=col; o.data.materials.append(m)
    c=bpy.data.curves.new(o.name+'_TXT','FONT'); c.body=label; c.size=.035; c.align_x='CENTER'; t=bpy.data.objects.new(o.name+'_TXT',c); scene.collection.objects.link(t); t.location=(shown.x-.01,shown.y,shown.z+.05); t.rotation_euler=(0,-math.pi/2,0); t.data.materials.append(m)
center=(mn+mx)*.5
cd=bpy.data.cameras.new('CMAI_BodyLength_Camera'); cam=bpy.data.objects.new('CMAI_BodyLength_Camera',cd); scene.collection.objects.link(cam); cam.location=(mn.x-(mx.x-mn.x)*2.5,center.y,center.z); cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler(); cd.type='ORTHO'; cd.ortho_scale=max(1,(mx.z-mn.z)*1.25); scene.camera=cam
scene.render.engine='BLENDER_WORKBENCH'; scene.render.resolution_x=640; scene.render.resolution_y=720; scene.render.resolution_percentage=100; scene.render.filepath=str(root/'data/generated/body_length_model_candidates.png'); scene.display.shading.light='STUDIO'; scene.display.shading.color_type='MATERIAL'; scene.display.shading.show_shadows=True; scene.display.shading.show_cavity=True
bpy.ops.render.render(write_still=True)
Path(root/'data/generated/body_length_model_candidates_uv.json').write_text(__import__('json').dumps({'y_min':mn.y,'y_max':mx.y,'z_min':mn.z,'z_max':mx.z,'points':proj},indent=2))
