"""Bounded silhouette-constrained single-pose experiment using existing IK."""
import bpy,json,sys
from pathlib import Path
from mathutils import Vector
root=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(root))
from creature_motion_ai.reference_walk import make_chain_applicator
from creature_motion_ai.auto_anatomy import detect_anatomy
out=Path(sys.argv[-1]).resolve(); bpy.ops.wm.open_mainfile(filepath=str(out/'standing_calibrated_cameras.blend'))
s=bpy.context.scene; arm=next(o for o in s.objects if o.type=='ARMATURE'); s.frame_set(1); bpy.context.view_layer.update()
baseline={p.name:p.matrix_basis.copy() for p in arm.pose.bones}; source_action=arm.animation_data.action if arm.animation_data else None
if arm.animation_data: arm.animation_data.action=None
camera=next(o for o in s.objects if o.type=='CAMERA' and o.name.startswith('CMAI_side_Calibration'))
candidates=detect_anatomy(arm)['selected_chains']
if not candidates: raise ValueError('No limb chain candidates; no pose changes made.')
# A camera-near chain is a geometric hypothesis, never a verified video identity.
candidate=min(candidates,key=lambda c:((arm.matrix_world@arm.pose.bones[c['bones'][0]].head)-camera.location).length)
names=candidate['bones']; leg='/'.join(names)
pts=[arm.matrix_world@arm.pose.bones[n].head for n in names]+[arm.matrix_world@arm.pose.bones[names[-1]].tail]
x=dict(names=names,points=pts,lengths=[(pts[i+1]-pts[i]).length for i in range(3)],normal=(pts[1]-pts[0]).cross(pts[2]-pts[0]).normalized(),matrices=[arm.matrix_world@arm.pose.bones[n].matrix.copy() for n in names])
apply=make_chain_applicator(arm,{leg:x}); rows=[]
step=.02*sum(x['lengths']); right=camera.rotation_euler.to_matrix()@Vector((1,0,0)); up=camera.rotation_euler.to_matrix()@Vector((0,1,0))
for i,delta in enumerate((Vector((0,0,0)),step*(-right+up),step*(right+up))):
 for p in arm.pose.bones: p.matrix_basis=baseline[p.name]
 bpy.context.view_layer.update(); result=apply(leg,pts[2]+Vector(delta),0)
 row=dict(candidate=i,leg=leg,bones=names,anatomy_confidence=candidate['confidence'],reference_identity='UNVERIFIED',delta=list(delta),solver=result)
 for view in ('side','front'):
  cam=next((o for o in s.objects if o.type=='CAMERA' and o.name.startswith('CMAI_'+view+'_Calibration')),None)
  if cam:
   s.camera=cam; s.render.filepath=str(out/f'pose_{i}_{view}.png'); bpy.ops.render.render(write_still=True)
 rows.append(row)
(out/'pose_trials.json').write_text(json.dumps(dict(trials=rows,accepted=False,source_action=source_action.name if source_action else None,reason='Hypothesis test only: reference leg correspondence and collision clearance not established; no Action created.'),indent=2))
