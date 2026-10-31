"""Find motion extrema and create an MP4-to-Blender timing map."""
import argparse, json
from pathlib import Path
import numpy as np

def extrema(values, prominence=0.0):
    if len(values) < 3: return []
    result=[]
    values=np.asarray(values,dtype=float)
    span=max(float(values.max()-values.min()),1e-8)
    for i in range(1,len(values)-1):
        local=max(abs(values[i]-values[i-1]),abs(values[i]-values[i+1]))
        if local/span < prominence: continue
        if (values[i]>=values[i-1] and values[i]>=values[i+1]) or (values[i]<=values[i-1] and values[i]<=values[i+1]): result.append(i)
    return result

def main():
    p=argparse.ArgumentParser(); p.add_argument('--motion',required=True); p.add_argument('--output',required=True); a=p.parse_args(); data=json.loads(Path(a.motion).read_text(encoding='utf-8')); frames=[f for f in data.get('frames',[]) if f.get('landmarks')]
    cx=[f['landmarks']['motion_center'][0] for f in frames]; cy=[f['landmarks']['motion_center'][1] for f in frames]; span=[f['landmarks']['motion_bottom'][1]-f['landmarks']['motion_top'][1] for f in frames]
    events=[]
    for name,values in [('body_x',cx),('body_y',cy),('body_span',span)]:
        smoothed=np.convolve(np.asarray(values,dtype=float),np.ones(5)/5,mode='same')
        for i in extrema(smoothed,0.08): events.append({'signal':name,'video_frame':frames[i]['frame'],'value':float(smoothed[i])})
    # The initial solver is frame-preserving; keep an explicit mapping so a
    # later pass can optimize a time warp rather than assuming equal speed.
    mapping=[{'video_frame':f['frame'],'blender_frame':i+1} for i,f in enumerate(frames)]
    result={'events':events,'mapping':mapping,'fps':data.get('fps',24.0),'notes':'Extrema are timing anchors; hidden legs still require gait inference.'}
    Path(a.output).write_text(json.dumps(result,indent=2),encoding='utf-8'); print(json.dumps({'events':len(events),'frames':len(mapping),'output':a.output}))
if __name__=='__main__': main()
