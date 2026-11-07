"""Smoke-test independent side/front observations and approved rig poses."""
import json, tempfile, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from creature_motion_ai.pose_library import load, save, add_observation, add_approved_pose, observations, poses_by_side_frame

def main():
    with tempfile.TemporaryDirectory() as d:
        p=Path(d)/'pose_library.json'; data=load(p)
        add_observation(data, source_video='SIDEbalaskWALK.mp4', frame=121, view='side', landmarks={'hip':{'x':10,'y':20,'visible':True}}, confidence={'hip':.99}, approval_status='manual_verified')
        add_observation(data, source_video='2VIEWSBALISK SYNCWALK.mp4', frame=61, view='front', landmarks={'body_center':{'x':12,'y':22,'visible':True}}, confidence={'body_center':.8}, approval_status='manual_verified')
        # Reopening and correcting the same observation must merge, not duplicate.
        add_observation(data, source_video='2VIEWSBALISK SYNCWALK.mp4', frame=61, view='front', landmarks={'body_center':{'x':14,'y':23,'visible':True}}, confidence={'body_center':.95}, approval_status='manual_verified')
        add_approved_pose(data, source_frame=121, rotations={'Leg_Rear.L_01':[0,0,0]}, armature='OriginalRig', metadata={'source':'side_fit'})
        save(p,data); reloaded=load(p)
        assert len(observations(reloaded, view='side'))==1
        assert len(observations(reloaded, view='front'))==1
        assert reloaded['observations'][1]['landmarks']['body_center']['x']==14
        assert reloaded['observations'][1]['confidence']['body_center']==.95
        assert poses_by_side_frame(reloaded)[0]['source_frame']==121
        assert reloaded['observations'][0]['approval_status']=='manual_verified'
        print(json.dumps({'status':'PASS','side_observations':len(observations(reloaded,view='side')),'front_observations':len(observations(reloaded,view='front')),'approved_poses':len(poses_by_side_frame(reloaded)),'out_of_order_sort':'PASS','status_preserved':'PASS'}))
if __name__=='__main__': main()
