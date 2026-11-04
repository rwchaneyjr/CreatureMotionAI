import bpy, json, math
from pathlib import Path
from mathutils import Vector

root=Path(r'C:\Users\rober\CreatureMotionAI')
blend=root/'data/generated/body_landmark_confirmation.blend'
out=root/'data/generated/ground_contact_candidates.json'
img=root/'data/generated/ground_contact_closeup.png'
bpy.ops.wm.open_mainfile(filepath=str(blend))
scene=bpy.context.scene
arm=next(o for o in scene.objects if o.type=='ARMATURE')
mesh=next(o for o in scene.objects if o.type=='MESH')
vg=None
for name in ('Leg_Rear.L_03','Leg_Rear.L.03','Leg_Rear_L_03'):
    vg=mesh.vertex_groups.get(name)
    if vg: break
if vg is None:
    raise RuntimeError('Leg_Rear.L_03 vertex group not found')
deps=bpy.context.evaluated_depsgraph_get(); ev=mesh.evaluated_get(deps)
me=ev.to_mesh(); mw=ev.matrix_world
rows=[]
for v in me.vertices:
    w=0.0
    try: w=vg.weight(v.index)
    except RuntimeError: pass
    if w>=0.20:
        p=mw@v.co; rows.append({'index':v.index,'weight':w,'xyz':[p.x,p.y,p.z]})
ev.to_mesh_clear()
rows.sort(key=lambda r:r['xyz'][2])
top=rows[:50]
cluster=Vector((sum(r['xyz'][0] for r in top)/len(top),sum(r['xyz'][1] for r in top)/len(top),sum(r['xyz'][2] for r in top)/len(top)))
zmin=top[0]['xyz'][2]
spread=max(math.dist(r['xyz'],cluster) for r in top)
result={'status':'CANDIDATE_ONLY','vertex_group':vg.name,'weighted_vertex_count':len(rows),'lowest_z':zmin,'candidate_centroid':[cluster.x,cluster.y,cluster.z],'candidate_spread':spread,'lowest_vertices':top,'decision':'UNCONFIRMED','reason':'A low coherent cluster was found, but the video correspondence and intended contact region still require visual confirmation.'}
out.write_text(json.dumps(result,indent=2))
# Make a close-up diagnostic scene with candidate points visible.
for i,r in enumerate(top[:12]):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=12, ring_count=6, radius=0.018, location=r['xyz'])
    o=bpy.context.object; o.name=f'CMAI_GroundCandidate_{i:02d}'
    mat=bpy.data.materials.new(o.name+'MAT'); mat.diffuse_color=(1.0,0.05,0.05,1.0); o.data.materials.append(mat)
allpts=[mesh.matrix_world@Vector(c) for c in mesh.bound_box]
mn=Vector((min(p.x for p in allpts),min(p.y for p in allpts),min(p.z for p in allpts))); mx=Vector((max(p.x for p in allpts),max(p.y for p in allpts),max(p.z for p in allpts)))
camd=bpy.data.cameras.new('CMAI_GroundCloseup_Camera'); cam=bpy.data.objects.new('CMAI_GroundCloseup_Camera',camd); scene.collection.objects.link(cam)
cam.location=(mn.x-(mx.x-mn.x)*1.0,cluster.y,cluster.z+0.1); target=cluster; cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler(); camd.type='ORTHO'; camd.ortho_scale=max(0.35,(mx.z-mn.z)*0.35); scene.camera=cam
scene.render.engine='BLENDER_WORKBENCH'; scene.render.resolution_x=1000; scene.render.resolution_y=700; scene.render.resolution_percentage=100; scene.render.filepath=str(img)
scene.display.shading.light='STUDIO'; scene.display.shading.color_type='MATERIAL'; scene.display.shading.show_shadows=True; scene.display.shading.show_cavity=True
bpy.ops.render.render(write_still=True)
