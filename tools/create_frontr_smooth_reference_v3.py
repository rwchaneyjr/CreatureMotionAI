import bpy, os
from mathutils import Quaternion, Vector
scene=bpy.context.scene; arm=bpy.data.objects.get('CrimsonSpineBehemoth_Rig'); mesh=bpy.data.objects.get('CrimsonSpineBehemoth_Mesh'); ns=['Leg_Front.R_01','Leg_Front.R_02','Leg_Front.R_03']
scene.frame_set(1); bpy.context.view_layer.update(); base={n:arm.pose.bones[n].rotation_quaternion.copy() for n in ns}
def qx(a): return Quaternion((1,0,0),a)
act=bpy.data.actions.new('CMAI_FrontR_SmoothReference_v3'); arm.animation_data_create(); arm.animation_data.action=act
def key(f,a):
 scene.frame_set(f)
 for n in ns:
  p=arm.pose.bones[n]; p.rotation_mode='QUATERNION'; p.rotation_quaternion=qx(a.get(n,0))@base[n]; p.keyframe_insert('rotation_quaternion',frame=f)
key(1,{})
key(8,{'Leg_Front.R_01':-0.48,'Leg_Front.R_02':0.16,'Leg_Front.R_03':0.0})
key(15,{'Leg_Front.R_01':0.52,'Leg_Front.R_02':-0.20,'Leg_Front.R_03':0.0})
key(22,{'Leg_Front.R_01':0.62,'Leg_Front.R_02':-0.10,'Leg_Front.R_03':0.0})
key(27,{'Leg_Front.R_01':-0.18,'Leg_Front.R_02':0.08,'Leg_Front.R_03':0.0})
key(30,{})
scene.world.color=(1,1,1); cam=bpy.data.objects.get('CMAI_FrontL_Proof_Camera'); cam.location=(-2.5,-1.8,-0.18); cam.data.type='ORTHO'; cam.data.ortho_scale=1.7; cam.rotation_euler=(Vector((0,-0.78,-0.10))-cam.location).to_track_quat('-Z','Y').to_euler(); scene.camera=cam
if mesh: mesh.hide_render=False
scene.render.engine='BLENDER_WORKBENCH'; scene.display.shading.light='STUDIO'; scene.display.shading.color_type='MATERIAL'; scene.display.shading.background_type='WORLD'; scene.display.shading.show_shadows=True; scene.display.shading.show_cavity=True
scene.render.resolution_x=1100; scene.render.resolution_y=700; scene.render.resolution_percentage=100; scene.render.image_settings.file_format='PNG'; scene.render.fps=24
d=os.path.abspath('data/generated/frontR_smooth_reference_v3_frames'); os.makedirs(d,exist_ok=True)
for i in range(1,121):
 scene.frame_set(((i-1)%30)+1); scene.render.filepath=os.path.join(d,f'frame_{i:04d}.png'); bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath('data/generated/frontR_smooth_reference_v3.blend'))
