"""Pose evidence must be video-specific, intact and consecutive, not named joints."""
import copy
import sys
import tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from creature_motion_ai.reference_evidence import file_hash, select_reference_pose

test_root=Path(__file__).resolve().parents[1]/'data/generated/pose_acceptance_20261116'
with tempfile.TemporaryDirectory(dir=test_root) as directory:
    video=Path(directory)/'fixture'; video.write_bytes(b'evidence-test')
    rows=[dict(frame=f,timestamp_seconds=(f-1)/24,status='MEASURED_IMAGE_ONLY',
               clipped=False,area_pixels=1000,bbox_xywh=[100,100,300,200],
               silhouette_centroid_xy=[250,200],lower_contour=[[x,300] for x in range(24)]) for f in range(1,8)]
    evidence=dict(source_sha256=file_hash(video),resolution=[640,360],frames=rows)
    selected=select_reference_pose(evidence,video)
    assert selected['eligible_frames']==5 and selected['leg_identity']=='UNVERIFIED'
    for change in ('hash','clipping','gaps','unmeasured'):
        invalid=copy.deepcopy(evidence)
        if change=='hash': invalid['source_sha256']='wrong'
        for row in invalid['frames']:
            if change=='clipping': row['clipped']=True
            if change=='gaps': row['frame']*=2
            if change=='unmeasured': row['status']='UNVERIFIED_SEGMENTATION'
        try: select_reference_pose(invalid,video)
        except ValueError: pass
        else: raise AssertionError('Invalid evidence accepted: '+change)
print('PASS: mismatched video, clipping, missing consecutive frames and unmeasured silhouettes rejected')
