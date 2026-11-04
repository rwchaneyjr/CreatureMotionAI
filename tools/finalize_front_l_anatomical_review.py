import json
from pathlib import Path
root=Path(__file__).resolve().parents[1]
m=json.loads((root/'data/generated/front_l_anatomical_measurements.json').read_text())
report={'status':'FAIL_PHYSICAL_VALIDATION','visual_evidence':'PASS_FAST_WORKBENCH_FRAMES_1_12_13_24','max_foot_orientation_deviation_deg':max(x['foot_orientation_deviation_deg'] for x in m['rows']),'provisional_joint_limits':'NOT_VERIFIED','ground_penetration_units':0.000677541,'trajectory_adjustment':'NOT_APPLIED','conclusion':'The candidate returns to its rest orientation at frames 1 and 24, but the 13.24 degree swing deviation and residual penetration require review; no naturalness PASS is claimed.'}
(root/'data/generated/front_l_anatomical_validation_report.json').write_text(json.dumps(report,indent=2))
