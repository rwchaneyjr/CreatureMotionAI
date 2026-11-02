"""Interpolate between collision-approved pose anchors in a new Blender file."""
import argparse, json
from pathlib import Path
import bpy
from mathutils import Euler

def snap(rig):
    return {b.name: (b.location.copy(), b.rotation_mode, b.rotation_euler.copy(), b.rotation_quaternion.copy(), b.scale.copy()) for b in rig.pose.bones}

def apply(rig, s, t):
    for n, (loc, mode, eul, quat, scale) in s.items():
        b = rig.pose.bones.get(n)
        if not b: continue
        b.location = loc.lerp(t[0], t[1]) if False else loc
        b.rotation_mode = mode
        b.rotation_euler = eul
        b.rotation_quaternion = quat
        b.scale = scale

def blend(a, b, u):
    out = {}
    for n, (la, mode, ea, qa, sa) in a.items():
        lb, _, eb, qb, sb = b[n]
        out[n] = (la.lerp(lb, u), mode, Euler(tuple(x + (y - x) * u for x, y in zip(ea, eb)), mode if mode in {'XYZ','XZY','YXZ','YZX','ZXY','ZYX'} else 'XYZ'), qa.slerp(qb, u), sa.lerp(sb, u))
    return out

def key(rig, frame):
    for b in rig.pose.bones:
        b.keyframe_insert('location', frame=frame, group=b.name)
        if b.rotation_mode == 'QUATERNION': b.keyframe_insert('rotation_quaternion', frame=frame, group=b.name)
        else: b.keyframe_insert('rotation_euler', frame=frame, group=b.name)
        b.keyframe_insert('scale', frame=frame, group=b.name)

def main():
    p=argparse.ArgumentParser(); p.add_argument('--source',required=True); p.add_argument('--report',required=True); p.add_argument('--output',required=True); a=p.parse_args()
    bpy.ops.wm.open_mainfile(filepath=str(Path(a.source).resolve()))
    rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
    report=json.loads(Path(a.report).read_text(encoding='utf-8'))
    anchors=[int(x['frame']) for x in report['frames'] if x.get('action')=='kept']
    if len(anchors)<2: raise RuntimeError('Need at least two collision-approved anchors')
    poses={}
    for f in anchors:
        bpy.context.scene.frame_set(f); poses[f]=snap(rig)
    start,end=min(anchors),max(anchors)
    for f in range(start,end+1):
        lo=max(x for x in anchors if x<=f); hi=min(x for x in anchors if x>=f)
        u=0.0 if hi==lo else (f-lo)/(hi-lo)
        s=blend(poses[lo],poses[hi],u); apply(rig,s,(u,)); key(rig,f)
    bpy.context.scene.frame_start=start; bpy.context.scene.frame_end=end
    bpy.ops.wm.save_as_mainfile(filepath=str(Path(a.output).resolve()))
    print(json.dumps({'output':str(a.output),'anchors':anchors,'frames':end-start+1}))
if __name__=='__main__': main()
