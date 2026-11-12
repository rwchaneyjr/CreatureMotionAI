import cv2, os
out='data/generated/frontL_three_pose_explicit_fullbody_corrected_5sec.mp4'
first=cv2.imread('data/generated/frontL_three_pose_explicit/corrected_fullbody_frames/frame_0001.png'); h,w=first.shape[:2]
wr=cv2.VideoWriter(out,cv2.VideoWriter_fourcc(*'mp4v'),24,(w,h))
for i in range(1,121): wr.write(cv2.imread(f'data/generated/frontL_three_pose_explicit/corrected_fullbody_frames/frame_{i:04d}.png'))
wr.release(); print(out,os.path.getsize(out))
