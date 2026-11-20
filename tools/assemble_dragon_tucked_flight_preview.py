"""Assemble the rendered dragon candidate and its reference comparison."""
from pathlib import Path
import json
import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/generated/dragon_quadruped_compatibility"
FRAMES = OUT / "flight_tucked_side_frames"
REFERENCE = Path(r"C:\Users\rober\Downloads\Untitled video.mp4")
PREVIEW = OUT / "dragon_flight_tucked_5sec.mp4"
COMPARE = OUT / "dragon_flight_tucked_side_by_side.mp4"
REPORT = OUT / "dragon_flight_tucked_report.json"
FPS = 24.0
COUNT = 120
PANEL = (800, 450)

def fit(frame, size=PANEL):
    w, h = size
    fh, fw = frame.shape[:2]
    scale = min(w / fw, h / fh)
    nw, nh = round(fw * scale), round(fh * scale)
    resized = cv2.resize(frame, (nw, nh), interpolation=cv2.INTER_AREA)
    canvas = np.zeros((h, w, 3), np.uint8)
    x, y = (w - nw) // 2, (h - nh) // 2
    canvas[y:y+nh, x:x+nw] = resized
    return canvas

def writer(path, size):
    result = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), FPS, size)
    if not result.isOpened():
        raise RuntimeError(f"Could not open MP4 writer: {path}")
    return result

files = [FRAMES / f"frame_{i:04d}.png" for i in range(1, COUNT + 1)]
missing = [str(p) for p in files if not p.is_file()]
if missing:
    raise FileNotFoundError(f"Missing rendered frames, first: {missing[0]}")
cap = cv2.VideoCapture(str(REFERENCE))
if not cap.isOpened():
    raise RuntimeError(f"Cannot open reference: {REFERENCE}")
ref_fps = cap.get(cv2.CAP_PROP_FPS)
ref_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
if ref_fps <= 0 or ref_count <= 0:
    raise RuntimeError("Reference MP4 has invalid timing metadata")

preview = writer(PREVIEW, PANEL)
comparison = writer(COMPARE, (PANEL[0] * 2, PANEL[1] + 34))
for i, path in enumerate(files):
    render = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if render is None:
        raise RuntimeError(f"Unreadable render frame: {path}")
    render = fit(render)
    preview.write(render)

    # Match by elapsed time; the two source clips have different frame rates.
    source_index = min(round(i * ref_fps / FPS), ref_count - 1)
    cap.set(cv2.CAP_PROP_POS_FRAMES, source_index)
    ok, reference = cap.read()
    if not ok:
        raise RuntimeError(f"Could not read reference frame {source_index}")
    reference = fit(reference)
    row = np.zeros((PANEL[1] + 34, PANEL[0] * 2, 3), np.uint8)
    cv2.putText(row, "REFERENCE  |  Untitled video.mp4", (16, 24), cv2.FONT_HERSHEY_SIMPLEX, .58, (240,240,240), 1, cv2.LINE_AA)
    cv2.putText(row, "CREATUREMOTIONAI  |  CMAI_Flight_Tucked", (PANEL[0] + 16, 24), cv2.FONT_HERSHEY_SIMPLEX, .52, (240,240,240), 1, cv2.LINE_AA)
    row[34:, :PANEL[0]] = reference
    row[34:, PANEL[0]:] = render
    comparison.write(row)

preview.release()
comparison.release()
cap.release()

# Verify the encoded files and representative frame readability.
checks = {}
for label, path in (("preview", PREVIEW), ("comparison", COMPARE)):
    v = cv2.VideoCapture(str(path))
    checks[label] = {
        "opened": bool(v.isOpened()),
        "fps": v.get(cv2.CAP_PROP_FPS),
        "frame_count": int(v.get(cv2.CAP_PROP_FRAME_COUNT)),
        "width": int(v.get(cv2.CAP_PROP_FRAME_WIDTH)),
        "height": int(v.get(cv2.CAP_PROP_FRAME_HEIGHT)),
    }
    v.release()
    if not checks[label]["opened"] or checks[label]["frame_count"] != COUNT:
        raise RuntimeError(f"Encoded video verification failed: {label}: {checks[label]}")

report = {
    "status": "PREVIEW_RENDERED; MOTION_VALIDATION_NOT_YET_ESTABLISHED",
    "source_reference": str(REFERENCE),
    "source_reference_fps": ref_fps,
    "source_reference_frames": ref_count,
    "source_reference_resolution": [1920, 1080],
    "candidate_blend": str(OUT / "CrimsonWingedDragon_flight_tucked.blend"),
    "candidate_action": "CMAI_Flight_Tucked",
    "candidate_method": "FLAP action retained for wing motion; leg tuck is a manually authored, rest-relative rotation adjustment, not motion-capture output.",
    "preservation": "Created from a separate test copy; original source blend and actions were not overwritten.",
    "output_fps": FPS,
    "output_frames": COUNT,
    "output_duration_seconds": COUNT / FPS,
    "reference_alignment": "Reference frames sampled by elapsed time (30 fps source to 24 fps output); preview covers source timestamps 0.000 through 4.958 s.",
    "videos": {"preview": str(PREVIEW), "side_by_side": str(COMPARE)},
    "encoded_video_checks": checks,
    "physical_validation": {
        "all_leg_contact_orientations": "UNVERIFIED",
        "wing_and_leg_mesh_collision": "UNVERIFIED",
        "foot_sliding": "NOT_APPLICABLE_TO_FLIGHT; foot trajectory realism remains visually judged",
        "ground_penetration": "NOT_APPLICABLE_TO_FLIGHT",
        "loop_boundary": "Visually inspected endpoint stills; not a full quantitative deformation/velocity continuity certification.",
    },
    "visual_limitations": "The candidate is an approximate flight pose using the existing FLAP action plus leg adjustments. It has not been proven to match the reference frame-by-frame; some limbs may be occluded by the wings/body.",
}
REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps({"report": str(REPORT), "videos": report["videos"], "checks": checks}, indent=2))
