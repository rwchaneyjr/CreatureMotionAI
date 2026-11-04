import json
from pathlib import Path
root=Path(__file__).resolve().parents[1]
o=json.loads((root/'data/generated/front_l_orientation_measurements.json').read_text())
c=json.loads((root/'data/generated/balisk_region_collision_report.json').read_text())
summary={'status':'FAIL_PHYSICAL_VALIDATION','region_collision':'PASS_NO_NONADJACENT_COLLISIONS_IN_TESTED_REGIONS','ground_contact':'FAIL_FRONT_L_0.000677541_UNITS','foot_orientation':'UNVERIFIED_ANATOMICAL_LIMITS_NOT_DEFINED','max_foot_angle_from_rest_deg':max(x['angle_from_rest_deg'] for x in o['frames']),'bend_direction':'UNVERIFIED','render_evidence':'BLOCKED_RENDER_DID_NOT_COMPLETE_WITHIN_RUNTIME_LIMIT','frames_checked':[11,12,13,14]}
(root/'data/generated/front_l_final_validation.json').write_text(json.dumps(summary,indent=2))
