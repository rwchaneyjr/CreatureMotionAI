import cv2
from pathlib import Path

old = Path(r'C:\Users\rober\CreatureMotionAI\data\generated\balisk_camera_baseline_walk_01\walk_5sec.mp4')
new = Path(r'C:\Users\rober\CreatureMotionAI\data\generated\e2e_balisk_test\builder\encode\walk_5sec.mp4')
out = Path(r'C:\Users\rober\CreatureMotionAI\data\generated\bending_history_side_by_side.mp4')
a, b = cv2.VideoCapture(str(old)), cv2.VideoCapture(str(new))
fps = a.get(cv2.CAP_PROP_FPS) or 24
wa,ha = int(a.get(cv2.CAP_PROP_FRAME_WIDTH)), int(a.get(cv2.CAP_PROP_FRAME_HEIGHT))
wb,hb = int(b.get(cv2.CAP_PROP_FRAME_WIDTH)), int(b.get(cv2.CAP_PROP_FRAME_HEIGHT))
w,h=640,360
writer=cv2.VideoWriter(str(out),cv2.VideoWriter_fourcc(*'mp4v'),fps,(w*2,h))
while True:
    oka,ia=a.read(); okb,ib=b.read()
    if not oka or not okb: break
    ia=cv2.resize(ia,(w,h)); ib=cv2.resize(ib,(w,h))
    cv2.rectangle(ia,(0,0),(w,36),(0,0,0),-1); cv2.rectangle(ib,(0,0),(w,36),(0,0,0),-1)
    cv2.putText(ia,'EARLIER BASELINE',(12,25),cv2.FONT_HERSHEY_SIMPLEX,.65,(0,255,255),2,cv2.LINE_AA)
    cv2.putText(ib,'CURRENT E2E',(12,25),cv2.FONT_HERSHEY_SIMPLEX,.65,(0,255,255),2,cv2.LINE_AA)
    writer.write(cv2.hconcat([ia,ib]))
a.release();b.release();writer.release();print(out)
