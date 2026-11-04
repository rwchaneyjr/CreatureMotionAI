import cv2, json, shutil
from pathlib import Path
import deeplabcut
import yaml

root=Path(r'C:\Users\rober\CreatureMotionAI'); video=root/'data/reference/goodspilitbalisk.mp4'; ann=json.loads((root/'data/generated/single_camera_verified_leg_landmarks.json').read_text())
work=root/'data/generated/dlc_balisk_project'; work.mkdir(parents=True,exist_ok=True); side_video=root/'data/generated/dlc_balisk_side_view.mp4'
cap=cv2.VideoCapture(str(video)); fps=cap.get(cv2.CAP_PROP_FPS) or 24; w=int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)); h=int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)); out=cv2.VideoWriter(str(side_video),cv2.VideoWriter_fourcc(*'mp4v'),fps,(w//2,h))
while True:
    ok,fr=cap.read()
    if not ok: break
    out.write(fr[:,:w//2])
cap.release(); out.release()
proj=work/'BaliskDLC-CreatureMotionAI-2026-11-03'
if not proj.exists():
    created=deeplabcut.create_new_project('BaliskDLC','CreatureMotionAI',[str(side_video)],working_directory=str(work),copy_videos=False,multianimal=False)
    proj=Path(created)
if not (proj/'config.yaml').is_file():
    candidates=list(proj.glob('*/config.yaml'))
    if candidates: proj=candidates[0].parent
config=proj/'config.yaml'; cfg=yaml.safe_load(config.read_text())
cfg['Task']='BaliskDLC'; cfg['scorer']='CreatureMotionAI'; cfg['bodyparts']=['hip','knee','ankle','foot']; cfg['video_sets']={str(side_video).replace('\\','/'): {}}
config.write_text(yaml.safe_dump(cfg,sort_keys=False))
label_dir=proj/'labeled-data'/side_video.stem; label_dir.mkdir(parents=True,exist_ok=True)
rows=[]
cap=cv2.VideoCapture(str(side_video))
for frame_str,data in ann['frames'].items():
    frame=int(frame_str); cap.set(cv2.CAP_PROP_POS_FRAMES,frame-1); ok,img=cap.read()
    if not ok: raise RuntimeError(f'frame {frame} unavailable')
    name=f'img{frame:06d}.png'; cv2.imwrite(str(label_dir/name),img)
    rows.append([f'labeled-data/{side_video.stem}/{name}']+[v for part in ('hip','knee','ankle','foot') for v in data[part]['uv']])
cap.release()
csv=label_dir/'CollectedData_CreatureMotionAI.csv'; header1=['scorer']+['CreatureMotionAI']*8; header2=['bodyparts']+sum(([p,p] for p in ('hip','knee','ankle','foot')),[]); header3=['coords']+['x','y']*4
with csv.open('w',newline='') as f:
    import csv as c; wtr=c.writer(f); wtr.writerow(header1); wtr.writerow(header2); wtr.writerow(header3); wtr.writerows(rows)
report={'status':'READY_FOR_MANUAL_LABEL_REVIEW','environment':'.venv-dlc','deeplabcut_version':deeplabcut.__version__,'project_path':str(proj),'side_video':str(side_video),'frames':[1,61,121,181,240],'bodyparts':['hip','knee','ankle','foot'],'verified_labels_imported':5,'training_started':False,'note':'Five verified frames are anchors only; insufficient by themselves for reliable training.'}
(root/'data/generated/dlc_setup_report.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
