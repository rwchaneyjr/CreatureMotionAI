import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from creature_motion_ai.camera_pose_fit import run_iteration
run_iteration(sys.argv[-1])
