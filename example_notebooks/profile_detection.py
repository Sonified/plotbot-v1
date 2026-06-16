"""
Quick profiler for magnetic hole detection pipeline.
Run from example_notebooks/ directory.

Produces a SHA-256 fingerprint of all detection outputs so we can
verify refactors are bit-identical.
"""
import sys, os
sys.path.insert(0, os.path.abspath('..'))
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from plotbot import print_manager as pm
pm.show_error = True
pm.show_warnings = False
pm.show_status = False
pm.show_debug = False
pm.show_datacubby = False
pm.show_processing = False

from plotbot import config
config.data_dir = '../data'
config.data_server = 'berkeley'

from magnetic_hole_finder.magnetic_hole_finder_core import HoleFinderSettings, _detect_magnetic_holes_logic
from magnetic_hole_finder.time_management import extend_time_range, clip_to_original_time_range, determine_sampling_rate, efficient_moving_average
from magnetic_hole_finder.data_management import download_and_prepare_high_res_mag_data
from collections import Counter
import numpy as np
import time
import hashlib
import json

from warnings import simplefilter
import warnings
simplefilter(action='ignore', category=DeprecationWarning)
warnings.filterwarnings("ignore", message="invalid value encountered")

trange = ['2024-09-30 01:00:00', '2024-09-30 03:00:00']

settings = HoleFinderSettings()
settings.depth_percentage_threshold = 0.25
settings.smoothing_window_seconds = 8.0
settings.mean_threshold = 0.8
settings.asymetric_peak_threshold = 0.25
settings.wide_angle_threshold = 15.0
settings.Bave_window_seconds = 20.0
settings.break_for_shallow_hole = True
settings.break_for_assymettry = True
settings.break_for_wide_angle = True
settings.break_for_small_threshold_cross = True
settings.break_for_complex_hole = True
settings.break_for_derivative_crossings = False
settings.search_in_progress_output = False

settings.OUTPUT_MAIN_PLOT = False
settings.SAVE_MAIN_PLOT = False
settings.IZOTOPE_MARKER_FILE_OUTPUT_MAX_AND_MIN = False
settings.EXPORT_AUDIO_FILES = False


class NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return super().default(obj)

def fingerprint_results(magnetic_holes, hole_minima, hole_maxima_pairs, magnetic_hole_details, counter):
    """Build a deterministic SHA-256 of all detection outputs."""
    h = hashlib.sha256()

    h.update(json.dumps(magnetic_holes, sort_keys=True, cls=NumpyEncoder).encode())
    h.update(json.dumps(hole_minima, sort_keys=True, cls=NumpyEncoder).encode())
    h.update(json.dumps([list(p) for p in hole_maxima_pairs], sort_keys=True, cls=NumpyEncoder).encode())

    for detail in magnetic_hole_details:
        h.update(json.dumps(detail, sort_keys=True, cls=NumpyEncoder).encode())

    h.update(json.dumps(dict(counter), sort_keys=True, cls=NumpyEncoder).encode())
    return h.hexdigest()


print(f"\n{'='*60}")
print(f"  PROFILING: {trange[0]} to {trange[1]}")
print(f"{'='*60}\n")

# ---- PHASE 1: Data download/prep ----
t0 = time.perf_counter()
extended_trange = extend_time_range(trange, max(settings.smoothing_window_seconds, settings.min_max_finding_smooth_window))
t1 = time.perf_counter()
print(f"[extend_time_range]       {t1-t0:.4f}s")

t0 = time.perf_counter()
dl_times, dl_br, dl_bt, dl_bn, dl_bmag = download_and_prepare_high_res_mag_data(extended_trange)
t1 = time.perf_counter()
print(f"[download_and_prepare]    {t1-t0:.4f}s  ({len(dl_bmag):,} samples)")

if dl_times is None:
    print("ERROR: No data returned. Aborting.")
    sys.exit(1)

# ---- PHASE 2: Smoothing ----
times_ext = dl_times
bmag_ext = dl_bmag

current_instrument_sampling_rate = settings.INSTRUMENT_SAMPLING_RATE
if settings.use_calculated_sampling_rate:
    from datetime import datetime
    from dateutil.parser import parse as dateutil_parse
    start_dt = dateutil_parse(extended_trange[0])
    end_dt = dateutil_parse(extended_trange[1])
    duration = (end_dt - start_dt).total_seconds()
    if duration > 0 and len(bmag_ext) > 0:
        current_instrument_sampling_rate = len(bmag_ext) / duration

t0 = time.perf_counter()
sampling_rate_for_smoothing = determine_sampling_rate(times_ext, current_instrument_sampling_rate, True)
t1 = time.perf_counter()
print(f"[determine_sampling_rate] {t1-t0:.4f}s  (SR={sampling_rate_for_smoothing:.1f} Hz)")

t0 = time.perf_counter()
bmag_slow_smooth_ext = efficient_moving_average(times_ext, bmag_ext, settings.smoothing_window_seconds, sampling_rate_for_smoothing, settings.mean_threshold)
t1 = time.perf_counter()
print(f"[slow_smooth (8s window)] {t1-t0:.4f}s")

t0 = time.perf_counter()
bmag_fast_smooth_ext = efficient_moving_average(times_ext, bmag_ext, settings.min_max_finding_smooth_window, sampling_rate_for_smoothing, settings.mean_threshold)
t1 = time.perf_counter()
print(f"[fast_smooth (0.3s win)]  {t1-t0:.4f}s")

# ---- PHASE 3: Clipping ----
t0 = time.perf_counter()
times_clipped, bmag_clipped = clip_to_original_time_range(times_ext, bmag_ext, trange)
_, bmag_slow_clipped = clip_to_original_time_range(times_ext, bmag_slow_smooth_ext, trange)
_, bmag_fast_clipped = clip_to_original_time_range(times_ext, bmag_fast_smooth_ext, trange)
_, br_clipped = clip_to_original_time_range(times_ext, dl_br, trange)
_, bt_clipped = clip_to_original_time_range(times_ext, dl_bt, trange)
_, bn_clipped = clip_to_original_time_range(times_ext, dl_bn, trange)
t1 = time.perf_counter()
print(f"[clip_to_original x6]    {t1-t0:.4f}s  ({len(bmag_clipped):,} clipped samples)")

# ---- PHASE 4: Detection loop ----
from magnetic_hole_finder import magnetic_hole_finder_core as mhf_core
mhf_core.hole_counter_core = Counter()

t0 = time.perf_counter()
results = _detect_magnetic_holes_logic(
    trange, settings, current_instrument_sampling_rate,
    times_ext, dl_br, dl_bt, dl_bn, bmag_ext,
    times_clipped, bmag_clipped, bmag_slow_clipped, bmag_fast_clipped
)
t1 = time.perf_counter()
detection_time = t1 - t0

magnetic_holes, hole_minima, hole_maxima_pairs, _, _, magnetic_hole_details, returned_counter = results

print(f"\n[detection_loop]          {detection_time:.4f}s")
print(f"Hole counts: {dict(returned_counter)}")
print(f"Confirmed holes: {returned_counter.get('confirmed', 0)}")

# ---- FINGERPRINT ----
fp = fingerprint_results(magnetic_holes, hole_minima, hole_maxima_pairs, magnetic_hole_details, returned_counter)
print(f"\n{'='*60}")
print(f"  FINGERPRINT: {fp}")
print(f"{'='*60}")

# Also dump the per-hole details for visual comparison
print(f"\n--- Per-hole detail dump ({len(magnetic_hole_details)} holes) ---")
for i, d in enumerate(magnetic_hole_details):
    print(f"  Hole {i:2d}: L={d['left_max_value_idx']:>8d}  R={d['right_max_value_idx']:>8d}  "
          f"min_idx={d['min_idx']:>8d}  min_val={d['min_value']:>10.4f}  "
          f"W={d['W_angle']:>8.4f}deg  zerox={d['zero_crossings']}")
