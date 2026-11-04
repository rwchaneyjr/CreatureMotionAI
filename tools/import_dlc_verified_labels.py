import csv, json, shutil
from pathlib import Path
import cv2

ROOT=Path(__file__).resolve().parents[1]
SUG=ROOT/'data/generated/dlc_training_suggestions.json'
VIDEO=ROOT/'data/generated/dlc_balisk_side_view.mp4'
PROJECT=ROOT/'data/generated/dlc_balisk_project/BaliskDLC-CreatureMotionAI-2026-11-03'
LAB=PROJECT/'labeled-data/dlc_balisk_side_view'
CSV_PATH=LAB/'CollectedData_CreatureMotionAI.csv'
OUT=ROOT/'data/generated/dlc_import_report.json'
PARTS=('hip','knee','ankle','foot')

def xy(v):
    u=v.get('uv',[0,0]); u=u.replace(',',' ').split() if isinstance(u,str) else u
    return float(u[0]),float(u[1])

def main():
    data=json.loads(SUG.read_text(encoding='utf-8'))
    with CSV_PATH.open(newline='',encoding='utf-8') as f: rows=list(csv.reader(f))
    existing={int(Path(r[0]).stem.replace('img','')) for r in rows[3:] if r}
    approved=[]
    for key,frame in data['frames'].items():
        if all(frame.get(p,{}).get('state')=='manual_verified' and frame[p].get('visible') for p in PARTS):
            approved.append((int(key),frame))
    new=[x for x in approved if x[0] not in existing]
    cap=cv2.VideoCapture(str(VIDEO)); imported=[]; invalid=[]
    for frame,pts in new:
        cap.set(cv2.CAP_PROP_POS_FRAMES,frame-1); ok,img=cap.read()
        if not ok: invalid.append({'frame':frame,'reason':'video_decode'}); continue
        name=f'img{frame:06d}.png'; cv2.imwrite(str(LAB/name),img)
        vals=[f'labeled-data/dlc_balisk_side_view/{name}']
        for p in PARTS:
            try: vals.extend([str(x) for x in xy(pts[p])])
            except Exception: invalid.append({'frame':frame,'reason':f'invalid_{p}'}); vals=[]; break
        if vals: rows.append(vals); imported.append(frame)
    cap.release()
    with CSV_PATH.open('w',newline='',encoding='utf-8') as f: csv.writer(f).writerows(rows)
    report={'unique_dlc_labeled_frames':len(existing)+len(imported),'newly_imported_frames':len(imported),'duplicates_skipped':len(approved)-len(new),'invalid_labels':invalid,'verified_landmarks_available':(len(existing)+len(imported))*4,'training_started':False,'training_ready':not invalid and len(imported)==len(new),'frames_imported':imported,'existing_frames':sorted(existing)}
    OUT.write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))
if __name__=='__main__': main()
