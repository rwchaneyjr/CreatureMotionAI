"""Measure approximate fixed-planar reprojection for the saved Rear.L action."""
import argparse, json, sys, math
from pathlib import Path

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--blend',required=True); ap.add_argument('--tracks',required=True); ap.add_argument('--report',required=True)
    argv=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else sys.argv[1:]; a=ap.parse_args(argv)
    import bpy
    from mathutils import Vector
    bpy.ops.wm.open_mainfile(filepath=str(Path(a.blend).resolve()))
    scene=bpy.context.scene; arm=next(o for o in scene.objects if o.type=='ARMATURE')
    chain=['Leg_Rear.L_01','Leg_Rear.L_02','Leg_Rear.L_03']; tracks=json.loads(Path(a.tracks).read_text())
    rows={int(x['frame']):x for x in tracks['frames'] if int(x['frame'])<=24}
    scene.frame_set(1); bpy.context.view_layer.update(); hip0=arm.matrix_world@arm.pose.bones[chain[0]].head; foot0=arm.matrix_world@arm.pose.bones[chain[2]].tail
    base=rows[1]['landmarks_2d']; base_vec=Vector((base['foot'][0]-base['hip'][0],base['foot'][1]-base['hip'][1])); px_per_unit=base_vec.length/max((foot0-hip0).length,1e-6)
    out=[]
    for f in range(1,25):
        scene.frame_set(f); bpy.context.view_layer.update(); foot=arm.matrix_world@arm.pose.bones[chain[2]].tail; d=foot-foot0
        pred=[base['foot'][0]+d.y*px_per_unit, base['foot'][1]-d.z*px_per_unit]; obs=rows[f]['landmarks_2d']['foot']; err=math.hypot(pred[0]-obs[0],pred[1]-obs[1])
        out.append({'frame':f,'predicted_foot_uv':pred,'observed_foot_uv':obs,'error_px':err,'confidence':rows[f]['confidence'].get('foot',0.0)})
    errs=[x['error_px'] for x in out]; result={'status':'APPROXIMATE_ONLY','projection':'fixed armature-local Y/Z plane; depth held at rest','frames':out,'mean_foot_error_px':sum(errs)/len(errs),'max_foot_error_px':max(errs),'metric_3d_claim':False,'note':'Only the tracked foot landmark is compared here; this is not calibrated 3D reconstruction.'}
    Path(a.report).write_text(json.dumps(result,indent=2),encoding='utf-8'); print(json.dumps({'mean_foot_error_px':result['mean_foot_error_px'],'max_foot_error_px':result['max_foot_error_px']}))
if __name__=='__main__': main()
