import argparse, json, sys
from pathlib import Path
def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--blend',required=True); ap.add_argument('--output',required=True); ap.add_argument('--render-dir',required=True); ap.add_argument('--report',required=True); argv=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else sys.argv[1:]; a=ap.parse_args(argv)
 import bpy
 from mathutils import Vector
 bpy.ops.wm.open_mainfile(filepath=str(Path(a.blend).resolve())); s=bpy.context.scene; arm=next(o for o in s.objects if o.type=='ARMATURE'); mesh=next(o for o in s.objects if o.type=='MESH'); names=['Leg_Rear.L_01','Leg_Rear.L_02','Leg_Rear.L_03']; s.frame_set(1); bpy.context.view_layer.update(); pts=[arm.matrix_world@arm.pose.bones[n].head for n in names]+[arm.matrix_world@arm.pose.bones[names[-1]].tail]; target=sum(pts,Vector())/len(pts)
 camd=bpy.data.cameras.new('CMAI_RearL_Closeup_Camera'); cam=bpy.data.objects.new('CMAI_RearL_Closeup_Camera',camd); s.collection.objects.link(cam); cam.location=target+Vector((-2.3,0.0,0.25)); camd.type='ORTHO'; camd.ortho_scale=.72; cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler(); s.camera=cam
 arm.show_in_front=True; arm.display_type='WIRE'; arm.data.display_type='BBONE'; mesh.show_transparent=True; mesh.color=(0.25,0.65,0.95,0.72); s.render.engine='BLENDER_WORKBENCH'; s.display.shading.light='STUDIO'; s.display.shading.color_type='MATERIAL'; s.display.shading.show_shadows=True; s.render.resolution_x=960; s.render.resolution_y=720; s.render.resolution_percentage=100; s.render.image_settings.file_format='PNG'; s.frame_start=1; s.frame_end=24; s.render.fps=24
 out=Path(a.render_dir); out.mkdir(parents=True,exist_ok=True)
 for f in range(1,25): s.frame_set(f); bpy.context.view_layer.update(); s.render.filepath=str(out/f'frame_{f:03d}.png'); bpy.ops.render.render(write_still=True)
 bpy.ops.wm.save_as_mainfile(filepath=str(Path(a.output).resolve())); report={'status':'CLOSEUP_RENDERED_FOR_VISUAL_REVIEW','action':arm.animation_data.action.name if arm.animation_data and arm.animation_data.action else None,'frames':[1,6,12,18,24],'camera':cam.name,'target':list(target),'render_dir':str(out.resolve()),'bones_visible':True,'mesh_transparent_overlay':True,'other_legs_animated':False}; Path(a.report).write_text(json.dumps(report,indent=2),encoding='utf-8'); print(json.dumps(report,indent=2))
if __name__=='__main__': main()
