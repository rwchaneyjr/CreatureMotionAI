"""CLI wrapper for the reusable CreatureMotionAI OpenCV analysis backend."""
import argparse, json
from pathlib import Path
from creature_motion_ai.video_analysis import analyze_video

def main():
    p=argparse.ArgumentParser(); p.add_argument('--video',required=True); p.add_argument('--output',required=True); p.add_argument('--start',type=int,default=0); p.add_argument('--end',type=int,default=None); a=p.parse_args()
    data=analyze_video(a.video,a.start,a.end)
    Path(a.output).parent.mkdir(parents=True,exist_ok=True); Path(a.output).write_text(json.dumps(data,indent=2),encoding='utf-8'); print(json.dumps({'status':'PASS','output':str(Path(a.output).resolve()),'frames':len(data['frames'])}))
if __name__=='__main__': main()
