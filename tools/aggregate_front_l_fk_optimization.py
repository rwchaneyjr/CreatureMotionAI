import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
rows = []
for d in range(9):
    p = root / "data" / "generated" / f"front_l_fk_sweep_{d}deg_proxy.json"
    data = json.loads(p.read_text(encoding="utf-8"))
    rows.append({
        "delta_deg": d,
        "max_penetration": data["max_penetration"],
        "worst_frames": data["worst_frames"],
        "runtime_seconds": data["runtime_seconds"],
        "knee_direction_metric": "proxy signed-side metric recorded per frame",
        "foot_orientation_metric": "not computed by clearance proxy; requires pose validator",
        "foot_endpoint_metric": "recorded per frame in proxy rows; baseline displacement comparison pending",
        "status": "diagnostic_candidate",
    })
best = min(rows, key=lambda x: x["max_penetration"])
report = {
    "status": "FAIL_PHYSICAL_VALIDATION_PENDING",
    "source": str(root / "data" / "generated" / "front_fk_test_fixed.blend"),
    "best_candidate": best,
    "candidates": rows,
    "preserved": ["original rig", "weights", "resting pose", "working Action"],
    "detailed_check": {
        "file": str(root / "data" / "generated" / "front_l_fk_sweep_8deg_detailed.json"),
        "frames": [12, 13],
        "result": "FAIL",
        "evidence": [
            "Front.R foot_below_ground at z=-0.2382100672",
            "1 coarse proxy self-collision pair; confirmed full BVH still pending",
        ],
    },
    "conclusion": "8 degrees is the best clearance candidate in the tested range, but Front.L is not physically validated and no candidate is promoted to final animation.",
}
out = root / "data" / "generated" / "front_l_fk_optimization_report.json"
out.write_text(json.dumps(report, indent=2), encoding="utf-8")
print(out)
