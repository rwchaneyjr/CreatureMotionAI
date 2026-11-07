import cv2, json
from pathlib import Path

src=Path(r'C:\Users\rober\Downloads\2VIEWSBALISK SYNCWALK.mp4')
out=Path(r'C:\Users\rober\CreatureMotionAI\data\generated\2views_syncwalk_audit_contact_sheet.png')
cap=cv2.VideoCapture(str(src)); fps=cap.get(cv2.CAP_PROP_FPS); n=int(cap.get(cv2.CAP_PROP_FRAME_COUNT)); w=int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)); h=int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
frames={}
for f in [1,61,121,181,240]:
    cap.set(cv2.CAP_PROP_POS_FRAMES,f-1); ok,im=cap.read()
    if ok: frames[f]=im
cap.release()
if not frames: raise RuntimeError('No frames decoded')
tiles=[]
for f,im in frames.items():
    left=im[:,:w//2]; right=im[:,w//2:]
    left=cv2.resize(left,(480,540)); right=cv2.resize(right,(480,540))
    cv2.putText(left,f'FRAME {f} VIEW A',(12,28),cv2.FONT_HERSHEY_SIMPLEX,.7,(0,255,255),2,cv2.LINE_AA)
    cv2.putText(right,f'FRAME {f} VIEW B',(12,28),cv2.FONT_HERSHEY_SIMPLEX,.7,(0,255,255),2,cv2.LINE_AA)
    tiles.append(cv2.hconcat([left,right]))
cv2.imwrite(str(out),cv2.vconcat(tiles))
report={'status':'TWO_VIEW_FILE_DECODED','source':str(src),'fps':fps,'frames':n,'resolution':[w,h],'panel_resolution':[w//2,h],'sample_frames':list(frames),'contact_sheet':str(out),'synchronization':'NOT_YET_VERIFIED','calibration':'NOT_AVAILABLE'}
out.with_name('2views_syncwalk_audit.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report))
