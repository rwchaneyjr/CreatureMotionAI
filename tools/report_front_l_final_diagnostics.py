import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
ds = [-3, -2, -1, 0, 1, 2, 3]
comp = []
for d in ds:
    p = root / "data" / "generated" / f"front_l_03_comp_{d}deg_proxy.json"
    comp.append(json.loads(p.read_text(encoding="utf-8")))
best = min(comp, key=lambda x: x["max_penetration"])
(root / "data" / "generated" / "front_l_03_compensation_report.json").write_text(json.dumps({
    "status": "FAIL_NOT_PHYSICALLY_VALID",
    "base_candidate": "+8 degrees Leg_Front.L_02",
    "candidates": comp,
    "best_proxy_candidate": best,
    "selection": "No candidate promoted; self-collision, orientation, and anatomical checks remain incomplete.",
    "preserved": ["original rig", "weights", "rest pose", "working Action"],
}, indent=2), encoding="utf-8")

(root / "data" / "generated" / "front_r_ground_diagnostic.json").write_text(json.dumps({
    "status": "FAIL_GROUND_CONTACT",
    "source": "front_l_fk_sweep_8deg_detailed.json",
    "frames": [12, 13],
    "evidence": [{"frame": f, "leg": "Front.R", "z": -0.238210067152977, "reason": "foot_below_ground"} for f in [12, 13]],
    "interpretation": "Front.R failure is present in the diagnostic scene and must be investigated separately; no Front.R changes were made.",
}, indent=2), encoding="utf-8")

(root / "data" / "generated" / "proxy_collision_pair_diagnostic.json").write_text(json.dumps({
    "status": "BLOCKED_TARGETED_PAIR_IDENTIFICATION",
    "source": "front_l_03_compensation_proxy_reports",
    "coarse_proxy": {"pair_count": 1, "confirmed": False},
    "next_required": "Instrument the proxy BVH to emit triangle/object regions and rerun a targeted detailed check.",
    "note": "The existing report does not expose the pair identities, so no collision region is being guessed.",
}, indent=2), encoding="utf-8")
