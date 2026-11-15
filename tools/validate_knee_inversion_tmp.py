import bpy, sys, json
from pathlib import Path
blend=Path(sys.argv[-2]); out=Path(sys.argv[-1]); bpy.ops.wm.open_mainfile(filepath=str(blend.resolve()))
s=bpy.context.scene; a=next(o for o in s.objects if o.type=='ARMATURE')
legs=['Front.L','Front.R','MidFront.L','MidFront.R','MidRear.L','MidRear.R','Rear.L','Rear.R']
def pts(leg):
 n=[f'Leg_{leg}_{i:02d}' for i in (1,2,3)]; return [a.matrix_world@a.pose.bones[x].head for x in n]+[a.matrix_world@a.pose.bones[n[-1]].tail]
s.frame_set(1); bpy.context.view_layer.update(); rest={l:(pts(l)[1]-pts(l)[0]).cross(pts(l)[2]-pts(l)[0]).normalized() for l in legs}
rows={l:[] for l in legs}
for f in range(1,121):
 s.frame_set(f); bpy.context.view_layer.update()
 for l in legs:
  p=pts(l); n=(p[1]-p[0]).cross(p[2]-p[0]); d=float(n.normalized().dot(rest[l])) if n.length else 1.0
  rows[l].append({'frame':f,'bend_dot':d,'inverted':d < -0.05})
summary={l:{'min_bend_dot':min(x['bend_dot'] for x in v),'inversion_count':sum(x['inverted'] for x in v),'worst_frame':min(v,key=lambda x:x['bend_dot'])['frame'],'status':'PASS' if not any(x['inverted'] for x in v) else 'FAIL'} for l,v in rows.items()}
result={'blend':str(blend),'summary':summary,'status':'PASS' if all(x['status']=='PASS' for x in summary.values()) else 'FAIL'}
out.write_text(json.dumps(result,indent=2)); print(json.dumps(summary,separators=(',',':')))
