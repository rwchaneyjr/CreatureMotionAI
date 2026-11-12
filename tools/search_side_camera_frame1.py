import bpy, json, sys
from pathlib import Path
from mathutils import Vector

blend,outdir=sys.argv[sys.argv.index('--')+1:]; out=Path(outdir); out.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(Path(blend).resolve())); s=bpy.context.scene; s.frame_set(1); mesh=bpy.data.objects['CrimsonSpineBehemoth_Mesh']
bb=[mesh.matrix_world@Vector(c) for c in mesh.bound_box]; cx=sum(v.x for v in bb)/8; cy=sum(v.y for v in bb)/8; cz=sum(v.z for v in bb)/8
cam=bpy.data.objects.get('CMAI_Search_Side_Camera') or bpy.data.objects.new('CMAI_Search_Side_Camera',bpy.data.cameras.new('CMAI_Search_Side_Camera')); 
if cam.name not in s.collection.objects: s.collection.objects.link(cam)
cam.data.type='ORTHO'; s.camera=cam; s.render.engine='BLENDER_WORKBENCH'; s.render.resolution_x=640; s.render.resolution_y=720; s.render.resolution_percentage=100
i=0
for sign in (-1,1):
 for scale in (1.3,1.8,2.3):
  for dz in (-.08,0,.08):
   cam.data.ortho_scale=scale; cam.location=(sign*3,cy,cz+dz); cam.rotation_euler=(Vector((cx,cy,cz+dz))-cam.location).to_track_quat('-Z','Y').to_euler(); s.render.filepath=str(out/f'candidate_{i:02d}.png'); bpy.ops.render.render(write_still=True); i+=1
bpy.ops.wm.save_as_mainfile(filepath=str(out/'camera_search.blend')); print(json.dumps({'candidates':i,'output_dir':str(out)}))
