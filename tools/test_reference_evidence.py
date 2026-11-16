"""Regression checks for cadence evidence: no one-frame or static-video PASS."""
import sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from creature_motion_ai.reference_evidence import estimate_recurrence

time=np.arange(240)
periodic=np.column_stack([np.sin(2*np.pi*time/40),np.cos(2*np.pi*time/40)])
result=estimate_recurrence(periodic,24)
assert result['status']=='SUPPORTED_VISUAL_RECURRENCE',result
assert result['candidate_period_frames'] in (40,80),result
assert result['blender_phase_offset_seconds'] is None
assert not result['individual_leg_cycle_verified']
assert estimate_recurrence(np.ones((240,10)),24)['status']=='UNVERIFIED'
assert estimate_recurrence(np.random.default_rng(7).normal(size=(240,24)),24)['status']=='UNVERIFIED'
assert estimate_recurrence(periodic[:10],24)['status']=='UNVERIFIED'
print('PASS: repeated pattern found; static, random and short clips remain unverified; no invented phase offset')
