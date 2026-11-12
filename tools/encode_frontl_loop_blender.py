import bpy, os
scene=bpy.context.scene
scene.sequence_editor_clear()
seq=scene.sequence_editor_create()
files=[{'name':f'frame_{i:04d}.png'} for i in range(1,121)]
strip=seq.strips.new_image('FrontL proof frames',os.path.abspath('data/generated/frontL_three_pose_explicit/frames/frame_0001.png'),channel=1,frame_start=1)
for i in range(2,121): strip.elements.append(f'frame_{i:04d}.png')
scene.frame_start=1; scene.frame_end=120; scene.render.fps=24
scene.render.engine='BLENDER_EEVEE'
scene.render.image_settings.file_format='FFMPEG'
scene.render.ffmpeg.format='MPEG4'; scene.render.ffmpeg.codec='MPEG4'; scene.render.ffmpeg.constant_rate_factor='MEDIUM'
scene.render.filepath=os.path.abspath('data/generated/frontL_three_pose_explicit/frontL_three_pose_loop_5sec.mp4')
bpy.ops.render.render(animation=True)
