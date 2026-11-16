"""Render camera candidates or selected profiles; never alter rig pose channels."""
import bpy, json, sys, math
from pathlib import Path
from mathutils import Vector

root=Path(__file__).resolve().parents[1]
out=Path(sys.argv[-2]); mode=sys.argv[-1]
request=json.loads((out/'request.json').read_text()) if (out/'request.json').exists() else {}
src=Path(request.get('standing_model',root/'data/generated/cmai_exact_standing_baseline_24f.blend'))
bpy.ops.wm.open_mainfile(filepath=str(src))
s=bpy.context.scene; s.frame_set(1); bpy.context.view_layer.update()
arm=next(o for o in s.objects if o.type=='ARMATURE')
meshes=[o for o in s.objects if o.type=='MESH' and any(m.type=='ARMATURE' and m.object==arm for m in o.modifiers)]
if not meshes: raise RuntimeError('No skinned meshes found')
pose_before={p.name:[list(r) for r in p.matrix_basis] for p in arm.pose.bones}
for o in s.objects:
 if o.type=='MESH': o.hide_render=o not in meshes
pts=[o.matrix_world@Vector(c) for o in meshes for c in o.bound_box]
center=(Vector(tuple(min(p[i] for p in pts) for i in range(3)))+Vector(tuple(max(p[i] for p in pts) for i in range(3))))/2
s.render.engine='BLENDER_WORKBENCH'; s.render.resolution_x=640; s.render.resolution_y=360; s.render.resolution_percentage=100
s.render.image_settings.file_format='PNG'; s.render.film_transparent=False
sh=s.display.shading; sh.light='FLAT'; sh.color_type='SINGLE'; sh.single_color=(1,1,1); sh.background_type='WORLD'; sh.show_shadows=False; sh.show_cavity=False; sh.show_specular_highlight=False
if s.world is None: s.world=bpy.data.worlds.new('Calibration world')
s.world.color=(0,0,0)
out.mkdir(parents=True,exist_ok=True)
if mode=='search':
 candidates=[]
 for view,azimuths in [('side',[-90,-75,90,105]),('front',[0,15,180,195])]:
  for az in azimuths:
   for elev in (0,12):
    for projection in ('ORTHO','PERSP'):
     candidates.append(dict(view=view,azimuth=az,elevation=elev,projection=projection,scale=2.6,lens=50))
else: candidates=json.loads((out/'selected.json').read_text())
profiles=[]
for i,c in enumerate(candidates):
 cd=bpy.data.cameras.new('CMAI_'+c['view']+'_Calibration'); cam=bpy.data.objects.new(cd.name,cd); s.collection.objects.link(cam); s.camera=cam
 az=math.radians(c['azimuth']); el=math.radians(c['elevation']); direction=Vector((math.sin(az)*math.cos(el),math.cos(az)*math.cos(el),math.sin(el)))
 cam.location=center+direction* (2.6*50/36); cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler(); cd.type=c['projection']; cd.ortho_scale=c['scale']; cd.lens=c['lens']; cd.sensor_width=36; cd.sensor_fit='HORIZONTAL'
 if mode!='search':
  zoom=c['zoom']; cd.ortho_scale/=zoom
  if cd.type=='PERSP': cd.lens*=zoom
  cd.shift_x=-c['dx']/640; cd.shift_y=c['dy']/640
 name=f'candidate_{i:02d}' if mode=='search' else c['view']+'_after'
 s.render.filepath=str(out/(name+'.png')); bpy.ops.render.render(write_still=True)
 profiles.append(dict(c,index=i,image=name+'.png',location=list(cam.location),rotation_euler=list(cam.rotation_euler),ortho_scale=cd.ortho_scale,focal_length=cd.lens,shift_x=cd.shift_x,shift_y=cd.shift_y))
assert pose_before=={p.name:[list(r) for r in p.matrix_basis] for p in arm.pose.bones}
(out/('candidates.json' if mode=='search' else 'camera_profiles.json')).write_text(json.dumps({'source':str(src),'bone_count':len(arm.data.bones),'pose_channels_unchanged':True,'profiles':profiles},indent=2))
if mode!='search': bpy.ops.wm.save_as_mainfile(filepath=str(out/'standing_calibrated_cameras.blend'))
