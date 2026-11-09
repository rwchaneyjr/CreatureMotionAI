import sys, glob, cv2, os
folder, dst = sys.argv[1], sys.argv[2]
loops = int(sys.argv[3]) if len(sys.argv) > 3 else 1
files=sorted(glob.glob(os.path.join(folder,'frame_*.png')))
first=cv2.imread(files[0]); h,w=first.shape[:2]
out=cv2.VideoWriter(dst,cv2.VideoWriter_fourcc(*'mp4v'),24,(w,h))
for _ in range(loops):
    for f in files:
        im=cv2.imread(f)
        if im is not None: out.write(im)
out.release(); print(dst,len(files[:120]),w,h)
