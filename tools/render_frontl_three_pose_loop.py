import bpy, os
scene=bpy.context.scene
scene.render.image_settings.file_format='PNG'
scene.render.resolution_x=800; scene.render.resolution_y=800; scene.render.resolution_percentage=100
scene.render.fps=24
frame_dir=os.path.abspath('data/generated/frontL_three_pose_explicit/frames')
os.makedirs(frame_dir,exist_ok=True)
for out_frame in range(1,121):
    src_frame=((out_frame-1)%30)+1
    scene.frame_set(src_frame)
    scene.render.filepath=os.path.join(frame_dir,f'frame_{out_frame:04d}.png')
    bpy.ops.render.render(write_still=True)
