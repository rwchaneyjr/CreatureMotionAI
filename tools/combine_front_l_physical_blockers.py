import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
pose = json.loads((root / "data/generated/front_l_front_r_physical_diagnostic.json").read_text())
detail = json.loads((root / "data/generated/front_l_fk_sweep_8deg_detailed.json").read_text())
report = {
    "status": "FAIL_PHYSICAL_VALIDATION",
    "front_l": {
        "ground_clearance": "FAIL",
        "max_proxy_penetration": 0.000678,
        "worst_frames": [12, 13],
        "foot_orientation": "UNVERIFIED",
        "anatomical_limits": "UNVERIFIED",
        "pose_evidence": str(root / "data/generated/front_l_front_r_physical_diagnostic.json"),
    },
    "front_r": {
        "endpoint_ground_check": "FAIL_OR_MISLEADING_REFERENCE",
        "endpoint_z": -0.238210067152977,
        "frames": [1, 12, 13, 24],
        "weighted_mesh_clearance": "PASS_AT_CALIBRATED_REFERENCE",
        "interpretation": "Endpoint bone tail is below the mesh-derived ground reference, but weighted foot geometry does not penetrate; investigate endpoint selection or contact definition before changing Front.R.",
        "changed_evaluated_transforms": False,
    },
    "collision_pairs": {
        "status": "UNVERIFIED",
        "coarse_pair_count": 1,
        "region_a": None,
        "region_b": None,
        "reason": "Existing coarse validator reports a count but not pair identities; targeted detailed check cannot be scoped safely yet.",
    },
    "detailed_check": {
        "frames": [12, 13],
        "result": "FAIL",
        "evidence": detail.get("frames", []),
    },
    "recommendation": "D: correct ground/contact and proxy instrumentation first; do not modify Front.R or promote Front.L yet.",
}
(root / "data/generated/front_l_physical_blockers_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
