import cv2, os
out='data/generated/frontL_three_pose_explicit_fullbody_5sec.mp4'
first=cv2.imread('data/generated/frontL_three_pose_explicit/fullbody_frames/frame_0001.png')
h,w=first.shape[:2]
writer=cv2.VideoWriter(out,cv2.VideoWriter_fourcc(*'mp4v'),24,(w,h))
for i in range(1,121): writer.write(cv2.imread(f'data/generated/frontL_three_pose_explicit/fullbody_frames/frame_{i:04d}.png'))
writer.release(); print(out,os.path.getsize(out))
