import json
from pathlib import Path
root=Path(__file__).resolve().parents[1]
report={'status':'FAIL_CORRECTION_NOT_FOUND','leg':'MidFront.R','baseline':'eight_leg_calibrated_24f.blend','max_penetration_before':0.05136294662952423,'max_penetration_after':None,'correction_candidates_tested':0,'reason':'Existing evidence shows near-rest joint angles but severe mesh clearance loss; no safe bounded target/orientation correction was demonstrated, so no candidate was promoted.','solver_update':'generic chain inspection, trajectory generation, candidate rejection API','other_legs_modified':False}
(root/'data/generated/midfrontr_generic_correction_report.json').write_text(json.dumps(report,indent=2))
