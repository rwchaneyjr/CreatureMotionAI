import cv2, json, math
from pathlib import Path
import numpy as np

src=Path(r'C:\Users\rober\Downloads\2VIEWSBALISK SYNCWALK.mp4')
root=Path(r'C:\Users\rober\CreatureMotionAI\data\generated')
cap=cv2.VideoCapture(str(src)); fps=cap.get(cv2.CAP_PROP_FPS); n=int(cap.get(cv2.CAP_PROP_FRAME_COUNT)); w=int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)); h=int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)); pw=w//2
motion_a=[]; motion_b=[]; fg_a=[]; fg_b=[]; bg_a=[]; bg_b=[]; prev=None; samples={}
for i in range(n):
    ok,im=cap.read()
    if not ok: break
    a=im[:,:pw]; b=im[:,pw:]
    # Creature color/foreground proxy: saturation and non-white pixels.
    def stats(x):
        hsv=cv2.cvtColor(x,cv2.COLOR_BGR2HSV); mask=((hsv[:,:,1]>35)&(hsv[:,:,2]<250)).astype(np.uint8)
        ys,xs=np.where(mask)
        if len(xs)<100: return 0.0,0.0,0.0,0.0
        return float(xs.mean()),float(ys.mean()),float(xs.min()),float(xs.max())
    sa=stats(a); sb=stats(b); fg_a.append(sa); fg_b.append(sb)
    if prev is None: ma=mb=0.0
    else:
        ma=float(np.mean(cv2.absdiff(cv2.cvtColor(prev[0],cv2.COLOR_BGR2GRAY),cv2.cvtColor(a,cv2.COLOR_BGR2GRAY))))
        mb=float(np.mean(cv2.absdiff(cv2.cvtColor(prev[1],cv2.COLOR_BGR2GRAY),cv2.cvtColor(b,cv2.COLOR_BGR2GRAY))))
    motion_a.append(ma); motion_b.append(mb); prev=(a,b)
    if i+1 in (1,61,121,181,240): samples[i+1]=im.copy()
cap.release()
def corr(x,y):
    x=np.asarray(x); y=np.asarray(y)
    if np.std(x)<1e-9 or np.std(y)<1e-9: return 0.0
    return float(np.corrcoef(x,y)[0,1])
offsets=range(-12,13); scores=[]
for off in offsets:
    if off>=0: x=motion_a[off:]; y=motion_b[:len(motion_b)-off]
    else: x=motion_a[:len(motion_a)+off]; y=motion_b[-off:]
    scores.append((off,corr(x,y)))
best=max(scores,key=lambda z:z[1])
def stability(rows):
    # centroid drift is evidence of camera/subject framing changes, not a camera proof.
    xs=[r[0] for r in rows if r[0]]; ys=[r[1] for r in rows if r[1]]
    return {'centroid_range_px':[float(max(xs)-min(xs)),float(max(ys)-min(ys))] if xs else None}
report={'status':'AUDIT_COMPLETE','source':str(src),'fps':fps,'frame_count':len(motion_a),'resolution':[w,h],'panel_resolution':[pw,h],'views':{'complete_frames':len(motion_a)==n,'same_creature':'SUPPORTED_BY_VISUAL_SAMPLING','different_angles':'SUPPORTED_BY_VISUAL_SAMPLING','camera_fixed':'UNVERIFIED','both_visible':'UNVERIFIED'},'synchronization':{'motion_signal':'mean grayscale frame difference','best_offset_frames':best[0],'best_correlation':best[1],'offset_scores':{str(o):c for o,c in scores},'decision':'UNVERIFIED' if best[1]<0.75 else 'PROVISIONAL'},'framing':{'view_a':stability(fg_a),'view_b':stability(fg_b)},'camera_calibration':'UNVERIFIED','anipose_readiness':'BLOCKED','tracking_reuse':{'sidebalisk_24_frame_landmarks':'EXIST','correspondence_to_new_video':'UNVERIFIED','leg_identity':'UNVERIFIED'},'reason':'No camera intrinsics/extrinsics or manually verified cross-view joint identities were supplied.'}
(root/'2views_syncwalk_full_audit.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
tiles=[]
for f,im in samples.items():
    a=cv2.resize(im[:,:pw],(480,540)); b=cv2.resize(im[:,pw:],(480,540)); cv2.putText(a,f'FRAME {f} A',(12,28),cv2.FONT_HERSHEY_SIMPLEX,.7,(0,255,255),2,cv2.LINE_AA); cv2.putText(b,f'FRAME {f} B',(12,28),cv2.FONT_HERSHEY_SIMPLEX,.7,(0,255,255),2,cv2.LINE_AA); tiles.append(cv2.hconcat([a,b]))
cv2.imwrite(str(root/'2views_syncwalk_full_audit_contact_sheet.png'),cv2.vconcat(tiles))
print(json.dumps({'frames':len(motion_a),'best_offset':best[0],'correlation':best[1],'anipose':'BLOCKED'}))
