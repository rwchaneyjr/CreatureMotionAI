import cv2, json
from pathlib import Path

src=Path(r'C:\Users\rober\Downloads\SIDEbalaskWALK.mp4')
out=Path(r'C:\Users\rober\CreatureMotionAI\data\generated\sidebalisk_reference_segment_001_024.mp4')
cap=cv2.VideoCapture(str(src))
fps=cap.get(cv2.CAP_PROP_FPS); total=int(cap.get(cv2.CAP_PROP_FRAME_COUNT)); w=int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)); h=int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
frames=[]
while len(frames)<24:
    ok,im=cap.read()
    if not ok: break
    frames.append(im)
cap.release()
if len(frames)!=24: raise RuntimeError(f'Expected 24 frames, got {len(frames)}')
writer=cv2.VideoWriter(str(out),cv2.VideoWriter_fourcc(*'mp4v'),fps,(w,h))
for im in frames: writer.write(im)
writer.release()
thumbs=[]
for i in [0,5,11,17,23]:
    im=cv2.resize(frames[i],(640,360)); cv2.putText(im,f'REFERENCE frame {i+1}',(15,30),cv2.FONT_HERSHEY_SIMPLEX,.8,(0,255,255),2,cv2.LINE_AA); thumbs.append(im)
sheet=cv2.hconcat(thumbs)
sheet_path=out.with_name('sidebalisk_reference_segment_contact_sheet.png'); cv2.imwrite(str(sheet_path),sheet)
report={'status':'REFERENCE_SEGMENT_READY','source':str(src),'output':str(out),'fps':fps,'source_frame_count':total,'resolution':[w,h],'selected_source_frames':[1,6,12,18,24],'note':'Leg identity and landmarks remain unverified; this segment is prepared for review only.'}
out.with_name('sidebalisk_reference_segment_report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report))
