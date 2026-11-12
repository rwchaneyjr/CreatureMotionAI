import cv2, os
out='data/generated/frontL_three_pose_explicit_reversed_fullbody_5sec.mp4'; d='data/generated/frontL_three_pose_explicit_reversed/fullbody_frames'
first=cv2.imread(f'{d}/frame_0001.png'); h,w=first.shape[:2]; wr=cv2.VideoWriter(out,cv2.VideoWriter_fourcc(*'mp4v'),24,(w,h))
for i in range(1,121): wr.write(cv2.imread(f'{d}/frame_{i:04d}.png'))
wr.release(); print(out,os.path.getsize(out))
