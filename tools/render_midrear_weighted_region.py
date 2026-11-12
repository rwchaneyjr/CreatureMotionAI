import bpy,sys
from pathlib import Path
from mathutils import Vector
args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else sys.argv[1:]
blend,out_dir=args[:2]; leg=args[2] if len(args)>2 else 'MidRear.L'; out=Path(out_dir); out.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(Path(blend).resolve())); s=bpy.context.scene
arm=bpy.data.objects['CrimsonSpineBehemoth_Rig']; src=bpy.data.objects['CrimsonSpineBehemoth_Mesh']
bones=[f'Leg_{leg}_{i:02d}' for i in (1,2,3)]; groups={g.name:i for i,g in enumerate(src.vertex_groups)}
ids=set()
for v in src.data.vertices:
    if any(groups.get(b) in [w.group for w in v.groups] for b in bones): ids.add(v.index)
faces=[]; used=set()
for poly in src.data.polygons:
    if all(i in ids for i in poly.vertices): faces.append(tuple(poly.vertices)); used.update(poly.vertices)
used=sorted(used); rem={old:i for i,old in enumerate(used)}; verts=[src.data.vertices[i].co.copy() for i in used]; faces2=[tuple(rem[i] for i in f) for f in faces]
me=bpy.data.meshes.new('CMAI_MidRearL_WeightedRegion_Mesh'); me.from_pydata(verts,[],faces2); me.update(); reg=bpy.data.objects.new('CMAI_MidRearL_WeightedRegion',me); s.collection.objects.link(reg); reg.matrix_world=src.matrix_world.copy()
mat=bpy.data.materials.new('CMAI_MidRearL_BRIGHT'); mat.diffuse_color=(1.0,0.02,0.02,1.0); mat.metallic=0; mat.roughness=.25; me.materials.append(mat)
for b in bones:
    vg=reg.vertex_groups.new(name=b); old=src.vertex_groups.get(b)
    if old:
        for ni,oi in enumerate(used):
            try: w=old.weight(oi); vg.add([ni],w,'REPLACE')
            except RuntimeError: pass
mod=reg.modifiers.new('CMAI_MidRearL_Armature','ARMATURE'); mod.object=arm
src.hide_render=True; src.hide_viewport=True
cam=bpy.data.objects.get('CMAI_MidRear_Region_Camera')
if not cam: cam=bpy.data.objects.new('CMAI_MidRear_Region_Camera',bpy.data.cameras.new('CMAI_MidRear_Region_Camera')); s.collection.objects.link(cam)
cam.data.type='ORTHO'; cam.data.ortho_scale=.6; cam.location=(-3,0.0,-.12); cam.rotation_euler=(Vector((0,0.0,-.12))-cam.location).to_track_quat('-Z','Y').to_euler(); s.camera=cam
s.render.engine='BLENDER_WORKBENCH'; s.render.resolution_x=960; s.render.resolution_y=540; s.render.resolution_percentage=100; s.render.image_settings.file_format='PNG'
rows=[]
for name,fr in [('planted',1),('high_lift',48),('forward_swing',68)]:
 s.frame_set(fr); bpy.context.view_layer.update(); ev=reg.evaluated_get(bpy.context.evaluated_depsgraph_get()); em=ev.to_mesh(); pts=[ev.matrix_world@v.co for v in em.vertices]; ev.to_mesh_clear(); mn=(min(p.x for p in pts),min(p.y for p in pts),min(p.z for p in pts)); mx=(max(p.x for p in pts),max(p.y for p in pts),max(p.z for p in pts)); rows.append({'pose':name,'frame':fr,'vertex_count':len(pts),'bbox_min':list(mn),'bbox_max':list(mx)})
 s.render.filepath=str(out/f'{name}.png'); bpy.ops.render.render(write_still=True)
Path(out/'weighted_region_report.json').write_text(__import__('json').dumps({'bones':bones,'selected_vertices':len(used),'selected_faces':len(faces2),'poses':rows,'status':'DIAGNOSTIC_ONLY'},indent=2))
print({'vertices':len(used),'faces':len(faces2),'out':str(out)})
