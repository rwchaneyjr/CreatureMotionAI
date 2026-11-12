import bpy, json, sys
from pathlib import Path
from mathutils import Vector

blend, out_blend, out_png = sys.argv[sys.argv.index('--')+1:]
bpy.ops.wm.open_mainfile(filepath=str(Path(blend).resolve()))
s=bpy.context.scene; mesh=bpy.data.objects['CrimsonSpineBehemoth_Mesh']; s.frame_set(1)
corners=[mesh.matrix_world@Vector(c) for c in mesh.bound_box]
minx,maxx=min(v.x for v in corners),max(v.x for v in corners); miny,maxy=min(v.y for v in corners),max(v.y for v in corners); minz,maxz=min(v.z for v in corners),max(v.z for v in corners)
cx=(minx+maxx)/2; cy=(miny+maxy)/2; cz=(minz+maxz)/2; height=maxz-minz
cam=bpy.data.objects.get('CMAI_Auto_Side_Camera')
if not cam:
 data=bpy.data.cameras.new('CMAI_Auto_Side_Camera'); cam=bpy.data.objects.new('CMAI_Auto_Side_Camera',data); s.collection.objects.link(cam)
cam.data.type='ORTHO'; cam.data.ortho_scale=max(height*1.28,(maxy-miny)*1.25/(640/720)); cam.location=(-3.0,cy,cz); cam.rotation_euler=(Vector((cx,cy,cz))-cam.location).to_track_quat('-Z','Y').to_euler(); s.camera=cam
s.render.engine='BLENDER_WORKBENCH'; s.render.resolution_x=640; s.render.resolution_y=720; s.render.resolution_percentage=100; s.render.film_transparent=False; s.render.filepath=str(Path(out_png).resolve())
bpy.ops.wm.save_as_mainfile(filepath=str(Path(out_blend).resolve())); bpy.ops.render.render(write_still=True)
Path(str(out_png)+'.json').write_text(json.dumps({'status':'APPROXIMATE_SIDE_CAMERA','camera':'CMAI_Auto_Side_Camera','view_axis':'-X','ortho_scale':cam.data.ortho_scale,'target':[cx,cy,cz],'mesh_bbox_world':[[miny,minz],[maxy,maxz]],'metric_calibration':'UNVERIFIED','leg_identity':'UNVERIFIED'},indent=2))
print(json.dumps({'blend':out_blend,'render':out_png,'ortho_scale':cam.data.ortho_scale}))
