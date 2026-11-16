"""Camera-only alignment, numbered contour markers, and measured errors."""
import json,sys
from pathlib import Path
import cv2,numpy as np
from scipy.optimize import differential_evolution
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from creature_motion_ai.reference_evidence import foreground_mask
run=Path(sys.argv[1]); stage=sys.argv[2]; req=json.loads((run/"request.json").read_text())
cap=cv2.VideoCapture(req["video"]); cap.set(cv2.CAP_PROP_POS_FRAMES,int(req["frame"])-1)
ok,reference=cap.read(); cap.release()
if not ok: raise ValueError("Reference frame unavailable")
reference=cv2.resize(reference,(640,360)); ref=foreground_mask(reference)
if ref is None: raise ValueError("Reference silhouette unavailable")
ref=ref>0
def model_mask(name):
    image=cv2.imread(str(run/name))
    if image is None: raise ValueError(name+" unavailable")
    return cv2.cvtColor(image,cv2.COLOR_BGR2GRAY)>150
def metric(a,b):
    ya,xa=np.where(a); yb,xb=np.where(b)
    if not len(xb): return {"iou":0.,"centroid_error_px":999.,"edge_pixels":0}
    margin=int(min(xb.min(),639-xb.max(),yb.min(),359-yb.max()))
    return {"iou":float((a&b).sum()/max(1,(a|b).sum())),
            "centroid_error_px":float(np.hypot(xa.mean()-xb.mean(),ya.mean()-yb.mean())),
            "edge_pixels":int(b[0].sum()+b[-1].sum()+b[:,0].sum()+b[:,-1].sum()),
            "frame_margin_px":margin}
initial=model_mask("model_baseline.png")
if stage=="fit":
    def warp(p):
        z,dx,dy=p
        return cv2.warpAffine(initial.astype("uint8"),np.float32([[z,0,320*(1-z)+dx],[0,z,180*(1-z)+dy]]),(640,360),flags=cv2.INTER_NEAREST)>0
    def loss(p):
        m=metric(ref,warp(p))
        return 1-m["iou"]+.001*m["centroid_error_px"]+.025*max(0,8-m["frame_margin_px"])
    best=differential_evolution(loss,[(.78,1.22),(-55,55),(-30,30)],seed=7,maxiter=35,popsize=8,polish=True)
    z,dx,dy=map(float,best.x)
    adjustment={"zoom":z,"shift_x_delta":-dx/640,"shift_y_delta":dy/640,"predicted_only":metric(ref,warp(best.x)),"method":"camera only; validated by actual rerender"}
    (run/"camera_adjustment.json").write_text(json.dumps(adjustment,indent=2)); print(json.dumps(adjustment)); sys.exit()
aligned=model_mask("model_aligned.png"); before=metric(ref,initial); after=metric(ref,aligned)
if stage=="margin":
    x=np.where(aligned)[1]
    correction=max(0,12-int(x.min()))-max(0,12-int(639-x.max()))
    adjustment=json.loads((run/"camera_adjustment.json").read_text())
    adjustment["shift_x_delta"]-=correction/640
    adjustment["actual_render_margin_correction_px"]=int(correction)
    (run/"camera_adjustment.json").write_text(json.dumps(adjustment,indent=2))
    print(json.dumps({"needs_rerender":bool(correction),"correction_px":int(correction)})); sys.exit()
report=json.loads((run/"image_landmark_report.json").read_text())
legacy_path=run.parent/"legacy_video_motion.json"
if not legacy_path.exists(): legacy_path=run.parent.parent/"legacy_video_motion.json"
legacy=json.loads(legacy_path.read_text()) if legacy_path.exists() else {}
legacy_frame=next((x for x in legacy.get("frames",[]) if int(x.get("frame",-1))==int(req["frame"])),{})
candidate_feet=legacy_frame.get("leg_candidates",[])
visible_feet=[{"label":f"visible-side foot candidate {int(p['station'])+1}",
                "xy":[float(p["foot"][0]*640),float(p["foot"][1]*360)],
                "confidence":float(p.get("confidence",0.0)),"status":"UNVERIFIED_IDENTITY"}
               for p in candidate_feet if len(p.get("foot",[]))>=2]
def markers(mask):
    y,x=np.where(mask); left=int(x.min()); right=int(x.max())
    return [{"number":1,"label":"silhouette center","xy":[float(np.mean(x)),float(np.mean(y))]},
            {"number":2,"label":"left outline","xy":[left,float(np.median(y[x==left]))]},
            {"number":3,"label":"right outline","xy":[right,float(np.median(y[x==right]))]}]
ref_points=markers(ref); model_points=markers(aligned)
model_joints=report.get("projected_model_landmarks",[])
def marked(image,points,label,joints=()):
    out=image.copy(); cv2.rectangle(out,(0,0),(640,72),(20,20,20),-1)
    cv2.putText(out,label,(10,18),cv2.FONT_HERSHEY_SIMPLEX,.5,(255,255,255),1)
    for p in points:
        x,y=map(int,p["xy"]); cv2.circle(out,(x,y),5,(0,200,255),-1)
        cv2.putText(out,str(p["number"]),(x+7,y-7),cv2.FONT_HERSHEY_SIMPLEX,.45,(0,90,200),1)
        cv2.putText(out,f'{p["number"]} {p["label"]}: UNVERIFIED',(10,27+13*p["number"]),cv2.FONT_HERSHEY_SIMPLEX,.33,(255,255,255),1)
    for n,p in enumerate(joints,4):
        x,y=map(int,p["xy"])
        if 0<=x<640 and 72<=y<360:
            cv2.circle(out,(x,y),4,(255,180,30),-1)
            cv2.putText(out,str(n),(x+5,y-5),cv2.FONT_HERSHEY_SIMPLEX,.4,(255,180,30),1)
    return out
model=cv2.imread(str(run/"model_visual.png"))
if model is None: model=cv2.imread(str(run/"model_aligned.png"))
comparison=np.hstack([marked(reference,ref_points,"REFERENCE FRAME 36"),marked(model,model_points,"BLENDER ALIGNED CAMERA",model_joints)])
legend=np.full((max(30,18*len(model_joints)+10),1280,3),20,np.uint8)
for n,p in enumerate(model_joints,4):
    cv2.putText(legend,f'{n} Blender {p["name"]} ({p["bone"]}): VIDEO MATCH UNVERIFIED',
                (650,18*(n-3)),cv2.FONT_HERSHEY_SIMPLEX,.39,(255,180,30),1)
cv2.imwrite(str(run/"image_landmark_comparison.png"),np.vstack([legend,comparison]))
side_review=reference.copy()
model_review=model.copy()
ref_roles=("Rear","MidRear","MidFront","Front")
for i,p in enumerate(visible_feet,1):
    x,y=map(int,p["xy"]); role=ref_roles[i-1] if i<=len(ref_roles) else "Unknown"
    cv2.circle(side_review,(x,y),6,(0,180,255),-1); cv2.putText(side_review,f"{role}?",(x-12,y-10),cv2.FONT_HERSHEY_SIMPLEX,.39,(0,100,220),1)
right=[p for p in model_joints if ".R " in p.get("name","")]
colors=[(255,80,80),(80,210,80),(80,150,255),(220,120,255)]
for li,leg in enumerate(("Front.R","MidFront.R","MidRear.R","Rear.R")):
    pts={p["name"].split()[-1]:p for p in right if p["name"].startswith(leg+" ")}
    ordered=[pts.get(k) for k in ("hip","knee","ankle","foot")]
    ordered=[p for p in ordered if p is not None and 0<=p["xy"][0]<640 and 0<=p["xy"][1]<360]
    color=colors[li]
    for a,b in zip(ordered,ordered[1:]): cv2.line(model_review,tuple(map(int,a["xy"])),tuple(map(int,b["xy"])),color,2)
    for role,p in zip(("H","K","A","F"),ordered):
        x,y=map(int,p["xy"]); cv2.circle(model_review,(x,y),4,color,-1); cv2.putText(model_review,role,(x+4,y-4),cv2.FONT_HERSHEY_SIMPLEX,.38,color,1)
cv2.putText(side_review,"VISIBLE SIDE: Rear? MidRear? MidFront? Front?; FOOT ID UNVERIFIED",(10,20),cv2.FONT_HERSHEY_SIMPLEX,.39,(0,100,220),1)
cv2.putText(model_review,"CANDIDATE .R CHAINS H/K/A/F; CORRESPONDENCE UNVERIFIED",(10,20),cv2.FONT_HERSHEY_SIMPLEX,.42,(255,140,0),1)
cv2.imwrite(str(run/"visible_side_landmark_review.png"),np.hstack([side_review,model_review]))
mask_visual=cv2.imread(str(run/"model_aligned.png"))
cv2.imwrite(str(run/"image_alignment_overlay.png"),cv2.addWeighted(reference,.65,mask_visual,.35,0))
report.update(reference_landmarks={"verified":[],"provisional":ref_points},
              camera_alignment={"before":before,"after":after,"adjustment":json.loads((run/"camera_adjustment.json").read_text()),"fullbody_visible":after["frame_margin_px"]>=3,"metric_calibration_verified":False},
              optimization={"status":"NOT_RUN","reason":"Exact video and frame lack verified anatomical correspondence."},
              pose_measurements={"baseline":"unchanged","candidate":"NOT GENERATED","verified_landmark_error_before_px":None,"verified_landmark_error_after_px":None},
              visible_side_review={"reference_foot_candidates":visible_feet,"model_leg_candidates":[p for p in model_joints if ".R " in p.get("name","")],"status":"UNVERIFIED_IDENTITY"},
              errors_px=[],
              unverified_contour_proxy_pairs=[{"number":a["number"],"reference_xy":a["xy"],"model_xy":b["xy"]} for a,b in zip(ref_points,model_points)])
(run/"image_landmark_report.json").write_text(json.dumps(report,indent=2))
(run/"verified_landmark_errors.csv").write_text("landmark,reference_x,reference_y,model_x,model_y,dx_px,dy_px,distance_px,confidence\n")
print(json.dumps({"before":before,"after":after,"status":report["status"]}))
