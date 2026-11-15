import bpy, json, sys
from pathlib import Path
from mathutils import Matrix

src=Path(sys.argv[-3]); traj=Path(sys.argv[-2]); dst=Path(sys.argv[-1])
bpy.ops.wm.open_mainfile(filepath=str(src.resolve()))
s=bpy.context.scene; arm=next(o for o in s.objects if o.type=='ARMATURE')
if not arm.animation_data or not arm.animation_data.action: raise RuntimeError('No active generated Action')
act=arm.animation_data.action
data=json.loads(traj.read_text(encoding='utf-8'))
by={int(r['frame']):r['legs'] for r in data['frames']}
legs=('Rear.R','Rear.L','MidRear.R','MidRear.L')
bones={b for leg in legs for b in by[1][leg]['basis']}
for layer in act.layers:
 for strip in layer.strips:
  for bag in strip.channelbags:
   for curve in list(bag.fcurves):
    if any(f'pose.bones["{b}"]' in curve.data_path for b in bones): bag.fcurves.remove(curve)
for f in range(1,42):
 s.frame_set(f)
 for leg in legs:
  for name,vals in by[f][leg]['basis'].items():
   p=arm.pose.bones[name]; p.rotation_mode='QUATERNION'; p.matrix_basis=Matrix(vals)
   p.keyframe_insert('rotation_quaternion',frame=f,group='B - '+leg)
for layer in act.layers:
 for strip in layer.strips:
  for bag in strip.channelbags:
   for curve in bag.fcurves:
    if 'rotation_quaternion' in curve.data_path:
     for k in curve.keyframe_points: k.interpolation='LINEAR'
    if len(curve.keyframe_points)>1 and not curve.modifiers: curve.modifiers.new('CYCLES')
s.frame_set(1); bpy.context.view_layer.update(); dst.parent.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=str(dst.resolve()))
print('SAVED',dst)
