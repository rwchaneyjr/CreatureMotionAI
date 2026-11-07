"""Synthetic regression test; no real video observation is approved here."""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from creature_motion_ai.static_pose_fit import static_fit_readiness

def main():
    data={"schema":"cmai_pose_library_v1","observations":[]}
    video="SYNTHETIC_TEST_ONLY.mp4"
    data["observations"]=[{"source_video":video,"frame":12,"view":"side",
      "landmarks":{"body_center":{"x":10,"y":20,"visible":True},"hip":{"x":30,"y":40,"visible":True}},
      "confidence":{"body_center":1.0,"hip":1.0},"approval_status":"manual_verified"}]
    report=static_fit_readiness(data, source_video=video, frame=12)
    assert report["status"]=="READY_FOR_BOUNDED_STATIC_FIT"
    assert report["missing_body_points"]==["snout","tail_base"]
    assert "snout" not in report["visible_approved_points"]
    print(json.dumps({"status":"PASS","unknown_points_not_invented":True,"partial_input_supported":True}))

if __name__ == "__main__": main()
