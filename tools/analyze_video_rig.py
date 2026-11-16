import argparse
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from creature_motion_ai.video_rig_analysis import analyze

def main():
    p=argparse.ArgumentParser(description='Conservative reference video + rig analysis; never creates an Action')
    p.add_argument('--video',required=True); p.add_argument('--rig-report',required=True); p.add_argument('--output',required=True)
    p.add_argument('--manual'); p.add_argument('--dlc')
    a=p.parse_args(); r=analyze(Path(a.video),Path(a.rig_report),Path(a.output),Path(a.manual) if a.manual else None,Path(a.dlc) if a.dlc else None)
    print({'status':r['status'],'output':str(Path(a.output)),'frames':r['video']['frames'],'selected_legs':r['rig']['selected_leg_count'],'approved_frames':r['joint_correspondence']['manual_approved_frames']})
if __name__=='__main__': main()
