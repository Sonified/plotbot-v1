"""
Jaye Candidate Batch Scan
Scans magnetic hole candidate time regions through the full pipeline.

Per region generates:
  1. Hole detection (main plot, marker file, audio, settings JSON)
  2. Low-res 4-panel showda_holes scatter plots
  3. High-res 8-panel showda_holes scatter plots
  4. |B| time series (full range)
  5. |B| time series (zoomed per-hole)
  6. FFT spectrograms at 3 resolutions (8192, 16384, 32768)
"""

import sys, os
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend — no plot windows

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_DIR = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, REPO_DIR)

# --- Plotbot setup ---
from plotbot import print_manager as pm
pm.show_error = True
pm.show_warnings = False
pm.show_status = True
pm.show_debug = False
pm.show_datacubby = False
pm.show_processing = False

from plotbot import config
config.data_dir = os.path.join(REPO_DIR, 'data')
config.data_server = 'berkeley'

# Load .env credentials for restricted data (proton_hr, epad_hr)
_env_path = os.path.join(SCRIPT_DIR, '.env')
if os.path.exists(_env_path):
    with open(_env_path) as _ef:
        for _line in _ef:
            _line = _line.strip()
            if _line and not _line.startswith('#') and '=' in _line:
                _k, _v = _line.split('=', 1)
                if _v.strip():
                    os.environ[_k.strip()] = _v.strip()
    _u = os.environ.get('PROTON_USERNAME', '')
    _p = os.environ.get('PROTON_PASSWORD', '')
    if _u and _p:
        from plotbot.server_access import server_access
        server_access._username = _u
        server_access._password = _p
        server_access.session.auth = (_u, _p)
        print(f"  Credentials loaded from .env")

from warnings import simplefilter
import warnings
simplefilter(action='ignore', category=DeprecationWarning)
warnings.filterwarnings("ignore", message="invalid value encountered")

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import time as _time

from plotbot import get_data as plotbot_get_data
from plotbot import mag_rtn, mag_rtn_4sa, epad, proton, showda_holes
from plotbot.showda_holes import _parse_marker_file

from magnetic_hole_finder.magnetic_hole_finder_core import (
    HoleFinderSettings, detect_magnetic_holes_and_generate_outputs
)
from magnetic_hole_finder.wavelet_scalogram import compute_spectrogram, render_spectrogram


# ============================================================
#  JAYE CANDIDATE REGIONS
# ============================================================
CANDIDATES = [
    {'label': 'E15_2023-03-15_00-12', 'trange': ['2023-03-15 00:00:00', '2023-03-15 12:00:00']},
    {'label': 'E21_2024-09-29_11-15', 'trange': ['2024-09-29 11:00:00', '2024-09-29 15:00:00']},
    {'label': 'E21_2024-09-30_01-03', 'trange': ['2024-09-30 01:00:00', '2024-09-30 03:00:00']},
    {'label': 'E21_2024-09-30_11-14', 'trange': ['2024-09-30 11:00:00', '2024-09-30 14:00:00']},
    {'label': 'E23_2025-03-22_00-03', 'trange': ['2025-03-22 00:00:00', '2025-03-22 03:00:00']},
]

# Which regions to run (0-indexed, or 'all')
RUN_REGIONS = 'all'

OUTPUT_ROOT = SCRIPT_DIR


# ============================================================
#  SETTINGS
# ============================================================
def make_settings():
    s = HoleFinderSettings()
    s.depth_percentage_threshold = 0.25
    s.smoothing_window_seconds = 8.0
    s.mean_threshold = 0.8
    s.break_for_shallow_hole = True
    s.break_for_assymettry = True
    s.break_for_wide_angle = True
    s.break_for_small_threshold_cross = True
    s.break_for_complex_hole = True
    s.break_for_derivative_crossings = False
    s.search_in_progress_output = False  # Suppress per-hole verbose output
    s.OUTPUT_MAIN_PLOT = True
    s.SAVE_MAIN_PLOT = True
    s.IZOTOPE_MARKER_FILE_OUTPUT_MAX_AND_MIN = True
    s.EXPORT_AUDIO_FILES = True
    s.MARKER_FILE_VERSION = 3
    return s


# ============================================================
#  PER-REGION PIPELINE
# ============================================================
def run_region(label, trange):
    import shutil
    region_dir = os.path.join(OUTPUT_ROOT, label)
    img_scatter       = os.path.join(region_dir, 'images', 'hodograms')
    img_ts            = os.path.join(region_dir, 'images', 'time_series')
    img_spec_full_raw  = os.path.join(region_dir, 'images', 'spectra', 'full', 'raw')
    img_spec_full_comp = os.path.join(region_dir, 'images', 'spectra', 'full', 'composite')
    img_spec_zoom_raw  = os.path.join(region_dir, 'images', 'spectra', 'zoomed', 'raw')
    img_spec_zoom_comp = os.path.join(region_dir, 'images', 'spectra', 'zoomed', 'composite')
    audio_dir          = os.path.join(region_dir, 'audio')
    for d in [img_scatter, img_ts, img_spec_full_raw, img_spec_full_comp,
              img_spec_zoom_raw, img_spec_zoom_comp, audio_dir]:
        os.makedirs(d, exist_ok=True)

    t_region_start = _time.perf_counter()
    _step_times = {}
    print(f"\n{'='*60}")
    print(f"  REGION: {label}")
    print(f"  trange: {trange[0]} to {trange[1]}")
    print(f"{'='*60}")

    # ----------------------------------------------------------
    # 1. HOLE DETECTION
    # ----------------------------------------------------------
    print("\n--- Step 1: Hole Detection ---")
    _t0 = _time.perf_counter()
    settings = make_settings()
    _tmp_det = os.path.join(region_dir, '_tmp_detection')
    os.makedirs(_tmp_det, exist_ok=True)
    results = detect_magnetic_holes_and_generate_outputs(trange, _tmp_det, settings)
    magnetic_holes, hole_minima, hole_maxima_pairs, times_clipped, bmag, magnetic_hole_details, returned_counter, marker_file_path = results
    _step_times['1_detection'] = _time.perf_counter() - _t0
    n_confirmed = returned_counter.get('confirmed', 0)
    print(f"  {n_confirmed} holes confirmed")

    # Relocate detection outputs into clean structure
    if marker_file_path:
        det_root = os.path.dirname(marker_file_path)
        for f in os.listdir(det_root):
            src = os.path.join(det_root, f)
            if f.endswith('.wav'):
                shutil.move(src, os.path.join(audio_dir, f))
            elif f.endswith('.txt'):
                shutil.move(src, os.path.join(audio_dir, f))
            elif f.endswith('.png'):
                shutil.move(src, os.path.join(img_ts, f))
            elif f.endswith('.json'):
                shutil.move(src, os.path.join(region_dir, 'run_settings.json'))
        # Update marker_file_path to new location
        marker_basename = os.path.basename(marker_file_path)
        marker_file_path = os.path.join(audio_dir, marker_basename)
    shutil.rmtree(_tmp_det, ignore_errors=True)

    # Enrich run_settings with data source metadata
    import json, glob
    settings_path = os.path.join(region_dir, 'run_settings.json')
    if os.path.exists(settings_path):
        with open(settings_path, 'r') as f:
            run_meta = json.load(f)
        date_prefix = trange[0][:10].replace('-', '')
        cdf_files = []
        if os.path.exists(config.data_dir):
            for root, _, files in os.walk(config.data_dir):
                for fn in sorted(files):
                    if date_prefix in fn and fn.endswith('.cdf'):
                        cdf_files.append(fn)
        run_meta['data_source'] = 'Parker Solar Probe / FIELDS'
        run_meta['data_type'] = 'mag_RTN (full cadence ~293 Hz) + mag_RTN_4_SA (4 Sa/s)'
        run_meta['detection_data_cadence_hz'] = round(run_meta.get('INSTRUMENT_SAMPLING_RATE', 293.0), 1)
        run_meta['source_cdf_files'] = cdf_files
        with open(settings_path, 'w') as f:
            json.dump(run_meta, f, indent=4)

    if not os.path.exists(marker_file_path or ''):
        print("  WARNING: No marker file produced. Skipping remaining steps.")
        return

    hole_intervals = _parse_marker_file(marker_file_path, pm)

    # Pre-load all instruments for this region's trange
    # (prevents stale cache from a previous region fooling showda_holes)
    print("  Pre-loading instruments for this region...")
    from plotbot import epad_hr, proton_hr
    plotbot_get_data(trange, mag_rtn_4sa, epad, proton, epad_hr, proton_hr)

    # ----------------------------------------------------------
    # 2. LOW-RES 4-PANEL SHOWDA_HOLES
    # ----------------------------------------------------------
    print("\n--- Step 2: Low-res 4-panel showda_holes ---")
    _t0 = _time.perf_counter()
    try:
        panel_defs = [
            {'x_data': mag_rtn_4sa.bmag, 'y_data': epad.centroids,     'marker_file': marker_file_path, 'title': '|B| vs EPAD Centroids'},
            {'x_data': mag_rtn_4sa.bmag, 'y_data': proton.anisotropy,  'marker_file': marker_file_path, 'title': '|B| vs Proton Anisotropy'},
            {'x_data': mag_rtn_4sa.bmag, 'y_data': proton.t_par,       'marker_file': marker_file_path, 'title': '|B| vs Proton T Parallel'},
            {'x_data': mag_rtn_4sa.bmag, 'y_data': proton.t_perp,      'marker_file': marker_file_path, 'title': '|B| vs Proton T Perpendicular'},
        ]
        fig, axes = showda_holes(trange, panel_definitions=panel_defs,
                                 main_title_fontsize=18, main_title_y=0.98, base_fontsize=14)
        if fig:
            fig.savefig(os.path.join(img_scatter, f'{label}_4panel.png'), bbox_inches='tight', dpi=150)
            plt.close(fig)
    except Exception as e:
        print(f"  ERROR: {e}")
    _step_times['2_showda_4panel'] = _time.perf_counter() - _t0

    # ----------------------------------------------------------
    # 3. HIGH-RES 8-PANEL SHOWDA_HOLES
    # ----------------------------------------------------------
    print("\n--- Step 3: High-res 8-panel showda_holes ---")
    _t0 = _time.perf_counter()
    try:
        panel_defs_hr = [
            {'x_data': mag_rtn_4sa.bmag, 'y_data': proton_hr.anisotropy,     'marker_file': marker_file_path, 'title': '|B| vs T Anisotropy (HR)'},
            {'x_data': mag_rtn_4sa.bmag, 'y_data': epad_hr.centroids,        'marker_file': marker_file_path, 'title': '|B| vs EPAD Centroids (HR)'},
            {'x_data': mag_rtn_4sa.bmag, 'y_data': proton_hr.t_par,          'marker_file': marker_file_path, 'title': '|B| vs T Parallel (HR)'},
            {'x_data': mag_rtn_4sa.bmag, 'y_data': proton_hr.t_perp,         'marker_file': marker_file_path, 'title': '|B| vs T Perpendicular (HR)'},
            {'x_data': mag_rtn_4sa.bmag, 'y_data': proton_hr.pressure_pperp, 'marker_file': marker_file_path, 'title': '|B| vs P Perpendicular (HR)'},
            {'x_data': mag_rtn_4sa.bmag, 'y_data': proton_hr.beta_ppar,      'marker_file': marker_file_path, 'title': '|B| vs Beta Parallel (HR)'},
            {'x_data': mag_rtn_4sa.bmag, 'y_data': proton_hr.anisotropy,     'marker_file': marker_file_path, 'title': '|B| vs P⊥/P∥ (HR)'},
            {'x_data': mag_rtn_4sa.bmag, 'y_data': proton_hr.density,        'marker_file': marker_file_path, 'title': '|B| vs Density (HR)'},
        ]
        fig_hr, axes_hr = showda_holes(trange, panel_definitions=panel_defs_hr,
                                       main_title_fontsize=18, main_title_y=0.99, base_fontsize=11)
        if fig_hr:
            fig_hr.savefig(os.path.join(img_scatter, f'{label}_8panel_HR.png'), bbox_inches='tight', dpi=150)
            plt.close(fig_hr)
    except Exception as e:
        print(f"  ERROR: {e}")
    _step_times['3_showda_8panel_HR'] = _time.perf_counter() - _t0

    # ----------------------------------------------------------
    # 4. |B| TIME SERIES (FULL RANGE) → summary/
    # ----------------------------------------------------------
    print("\n--- Step 4: |B| time series (full range) ---")
    _t0 = _time.perf_counter()
    try:
        plotbot_get_data(trange, mag_rtn_4sa)
        bmag_times = mag_rtn_4sa.bmag.datetime_array
        bmag_vals = mag_rtn_4sa.bmag.data
        bmag_series = pd.Series(bmag_vals, index=pd.DatetimeIndex(bmag_times))
        bmag_clipped = bmag_series[trange[0]:trange[1]]

        fig_ts, ax_ts = plt.subplots(figsize=(18, 5))
        ax_ts.plot(bmag_clipped.index, bmag_clipped.values, 'k-', linewidth=0.5, alpha=0.8)
        n_in_range = 0
        for h_start, h_end in hole_intervals:
            h_s = h_start.replace(tzinfo=None)
            h_e = h_end.replace(tzinfo=None)
            if h_s >= bmag_clipped.index[0] and h_e <= bmag_clipped.index[-1]:
                ax_ts.axvspan(h_s, h_e, alpha=0.2, color='red')
                n_in_range += 1
        ax_ts.set_xlabel('Time (UTC)')
        ax_ts.set_ylabel('|B| (nT)')
        ax_ts.set_title(f'|B| with {n_in_range} Detected Holes — {trange[0]} to {trange[1]}')
        ax_ts.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
        ax_ts.grid(True, linestyle=':', alpha=0.5)
        fig_ts.tight_layout()
        fig_ts.savefig(os.path.join(img_ts, f'{label}_full.png'), bbox_inches='tight', dpi=150)
        plt.close(fig_ts)
    except Exception as e:
        print(f"  ERROR: {e}")
    _step_times['4_timeseries_full'] = _time.perf_counter() - _t0

    # ----------------------------------------------------------
    # 5. |B| TIME SERIES (ZOOMED TO HOLE REGION) → summary/
    # ----------------------------------------------------------
    print("\n--- Step 5: Zoomed time series (hole region) ---")
    _t0 = _time.perf_counter()
    try:
        from datetime import timedelta
        if len(hole_intervals) > 0:
            first_hole_start = min(h[0] for h in hole_intervals).replace(tzinfo=None)
            last_hole_end = max(h[1] for h in hole_intervals).replace(tzinfo=None)
            hole_span = (last_hole_end - first_hole_start).total_seconds()
            pad = timedelta(seconds=max(30, hole_span * 0.1))
            zoom_start = first_hole_start - pad
            zoom_end = last_hole_end + pad
            zoom_data = bmag_clipped[zoom_start:zoom_end]

            fig_z, ax_z = plt.subplots(figsize=(18, 5))
            ax_z.plot(zoom_data.index, zoom_data.values, 'k-', linewidth=0.5, alpha=0.8)
            for h_start, h_end in hole_intervals:
                h_s = h_start.replace(tzinfo=None)
                h_e = h_end.replace(tzinfo=None)
                ax_z.axvspan(h_s, h_e, alpha=0.2, color='red')
            ax_z.set_xlabel('Time (UTC)')
            ax_z.set_ylabel('|B| (nT)')
            ax_z.set_title(f'|B| Zoomed to Hole Region — {n_confirmed} holes — {label}')
            ax_z.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
            ax_z.grid(True, linestyle=':', alpha=0.5)
            fig_z.tight_layout()
            fig_z.savefig(os.path.join(img_ts, f'{label}_zoomed.png'), bbox_inches='tight', dpi=150)
            plt.close(fig_z)
        else:
            print("  No holes found — skipping zoomed view.")
    except Exception as e:
        print(f"  ERROR: {e}")
    _step_times['5_timeseries_zoomed'] = _time.perf_counter() - _t0

    # ----------------------------------------------------------
    # 5b. CLUSTERED ZOOM VIEWS → zoom/
    # ----------------------------------------------------------
    print("\n--- Step 5b: Clustered zoom views ---")
    _t0 = _time.perf_counter()
    try:
        from datetime import timedelta
        if len(hole_intervals) >= 2:
            sorted_holes = sorted(hole_intervals, key=lambda h: h[0])
            naive_holes = [(h[0].replace(tzinfo=None), h[1].replace(tzinfo=None)) for h in sorted_holes]

            gaps = []
            for i in range(1, len(naive_holes)):
                gap_sec = (naive_holes[i][0] - naive_holes[i-1][1]).total_seconds()
                gaps.append((gap_sec, i))

            gaps.sort(reverse=True)
            target_clusters = min(5, max(2, len(naive_holes) // 5))
            n_splits = min(target_clusters - 1, len(gaps))
            split_indices = sorted([g[1] for g in gaps[:n_splits]])

            clusters = []
            prev = 0
            for si in split_indices:
                clusters.append(naive_holes[prev:si])
                prev = si
            clusters.append(naive_holes[prev:])

            print(f"  {len(clusters)} clusters from {len(naive_holes)} holes (target was {target_clusters})")

            for ci, cluster in enumerate(clusters):
                c_start = min(h[0] for h in cluster)
                c_end = max(h[1] for h in cluster)
                c_span = (c_end - c_start).total_seconds()
                pad = timedelta(seconds=max(5, c_span * 0.4))
                z_start = c_start - pad
                z_end = c_end + pad
                z_data = bmag_clipped[z_start:z_end]

                if z_data.empty:
                    continue

                fig_cz, ax_cz = plt.subplots(figsize=(16, 4))
                ax_cz.plot(z_data.index, z_data.values, 'k-', linewidth=0.8, alpha=0.9)
                for h_s, h_e in cluster:
                    ax_cz.axvspan(h_s, h_e, alpha=0.25, color='red')
                    hole_slice = bmag_clipped[h_s:h_e]
                    if not hole_slice.empty:
                        min_time = hole_slice.idxmin()
                        ax_cz.axvline(min_time, color='blue', alpha=0.6, linewidth=0.8)

                t0_str = c_start.strftime('%H:%M:%S')
                t1_str = c_end.strftime('%H:%M:%S')
                ax_cz.set_title(f'Cluster {ci+1}/{len(clusters)} — {len(cluster)} holes — {t0_str} to {t1_str}')
                ax_cz.set_xlabel('Time (UTC)')
                ax_cz.set_ylabel('|B| (nT)')
                ax_cz.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
                ax_cz.grid(True, linestyle=':', alpha=0.5)
                fig_cz.tight_layout()
                fig_cz.savefig(os.path.join(img_ts, f'{label}_cluster_{ci+1:02d}_{len(cluster)}holes.png'),
                               bbox_inches='tight', dpi=150)
                plt.close(fig_cz)

        elif len(hole_intervals) == 1:
            h_s = hole_intervals[0][0].replace(tzinfo=None)
            h_e = hole_intervals[0][1].replace(tzinfo=None)
            pad = timedelta(seconds=10)
            z_data = bmag_clipped[h_s - pad:h_e + pad]
            if not z_data.empty:
                fig_cz, ax_cz = plt.subplots(figsize=(16, 4))
                ax_cz.plot(z_data.index, z_data.values, 'k-', linewidth=0.8, alpha=0.9)
                ax_cz.axvspan(h_s, h_e, alpha=0.25, color='red')
                ax_cz.set_title(f'Single hole — {h_s.strftime("%H:%M:%S")}')
                ax_cz.set_xlabel('Time (UTC)')
                ax_cz.set_ylabel('|B| (nT)')
                ax_cz.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
                ax_cz.grid(True, linestyle=':', alpha=0.5)
                fig_cz.tight_layout()
                fig_cz.savefig(os.path.join(img_ts, f'{label}_cluster_01_1hole.png'),
                               bbox_inches='tight', dpi=150)
                plt.close(fig_cz)
        else:
            print("  No holes — skipping cluster zoom.")
    except Exception as e:
        print(f"  ERROR: {e}")
    _step_times['5b_cluster_zoom'] = _time.perf_counter() - _t0

    # ----------------------------------------------------------
    # 6. FFT SPECTROGRAMS (3 resolutions) → full + zoomed × raw + composite
    # ----------------------------------------------------------
    print("\n--- Step 6: FFT Spectrograms ---")
    _t0 = _time.perf_counter()
    try:
        from datetime import timedelta
        plotbot_get_data(trange, mag_rtn)
        bmag_hires_all = np.asarray(mag_rtn.bmag.data, dtype=np.float64)
        hires_times = pd.DatetimeIndex(mag_rtn.datetime_array)
        fs = 293.0
        t_start_full = pd.Timestamp(hires_times[0])

        bmag_ts_times = pd.DatetimeIndex(mag_rtn_4sa.bmag.datetime_array)
        bmag_ts_vals = np.asarray(mag_rtn_4sa.bmag.data, dtype=np.float64)

        zoom_trange = None
        if len(hole_intervals) > 0:
            first_hole = min(h[0] for h in hole_intervals).replace(tzinfo=None)
            last_hole = max(h[1] for h in hole_intervals).replace(tzinfo=None)
            hole_span = (last_hole - first_hole).total_seconds()
            pad = timedelta(seconds=max(30, hole_span * 0.1))
            zoom_start = first_hole - pad
            zoom_end = last_hole + pad
            zoom_mask = (hires_times >= zoom_start) & (hires_times <= zoom_end)
            if zoom_mask.any():
                zoom_trange = (zoom_start, zoom_end)

        for nperseg in [8192, 16384, 32768]:
            # --- FULL ---
            freqs, t_sec, pwr = compute_spectrogram(
                bmag_hires_all, fs, nperseg=nperseg, freq_range=(0.005, 50.0))

            fig_raw, ax_raw = render_spectrogram(
                freqs, t_sec, pwr, t_start=t_start_full,
                title=f'{label} — nperseg={nperseg}',
                save_path=os.path.join(img_spec_full_raw, f'{label}_spectrogram_{nperseg}.png'),
                dpi=150)
            plt.close(fig_raw)

            fig_comp, ax_comp = render_spectrogram(
                freqs, t_sec, pwr, t_start=t_start_full,
                title=f'{label} — nperseg={nperseg} + |B|',
                dpi=150)
            ax_ov = ax_comp.twinx()
            ax_ov.plot(bmag_ts_times.to_pydatetime(), bmag_ts_vals,
                       color='black', linewidth=0.6, alpha=0.85)
            ax_ov.set_ylabel('|B| (nT)', color='black')
            ax_ov.tick_params(axis='y', colors='black')
            ax_ov.set_xlim(ax_comp.get_xlim())
            fig_comp.tight_layout()
            fig_comp.savefig(os.path.join(img_spec_full_comp, f'{label}_spectrogram_{nperseg}.png'),
                             bbox_inches='tight', dpi=150)
            plt.close(fig_comp)

            # --- ZOOMED ---
            if zoom_trange:
                zoom_mask = (hires_times >= zoom_trange[0]) & (hires_times <= zoom_trange[1])
                bmag_zoom = bmag_hires_all[zoom_mask]
                t_start_zoom = pd.Timestamp(hires_times[zoom_mask][0])

                ts_zoom_mask = (bmag_ts_times >= zoom_trange[0]) & (bmag_ts_times <= zoom_trange[1])
                ts_zoom_times = bmag_ts_times[ts_zoom_mask]
                ts_zoom_vals = bmag_ts_vals[ts_zoom_mask]

                if len(bmag_zoom) > nperseg:
                    fz, tz, pz = compute_spectrogram(
                        bmag_zoom, fs, nperseg=nperseg, freq_range=(0.005, 50.0))

                    fig_zr, ax_zr = render_spectrogram(
                        fz, tz, pz, t_start=t_start_zoom,
                        title=f'{label} zoomed — nperseg={nperseg}',
                        save_path=os.path.join(img_spec_zoom_raw, f'{label}_spectrogram_{nperseg}.png'),
                        dpi=150)
                    plt.close(fig_zr)

                    fig_zc, ax_zc = render_spectrogram(
                        fz, tz, pz, t_start=t_start_zoom,
                        title=f'{label} zoomed — nperseg={nperseg} + |B|',
                        dpi=150)
                    ax_zov = ax_zc.twinx()
                    ax_zov.plot(ts_zoom_times.to_pydatetime(), ts_zoom_vals,
                                color='black', linewidth=0.6, alpha=0.85)
                    ax_zov.set_ylabel('|B| (nT)', color='black')
                    ax_zov.tick_params(axis='y', colors='black')
                    ax_zov.set_xlim(ax_zc.get_xlim())
                    fig_zc.tight_layout()
                    fig_zc.savefig(os.path.join(img_spec_zoom_comp, f'{label}_spectrogram_{nperseg}.png'),
                                   bbox_inches='tight', dpi=150)
                    plt.close(fig_zc)
                else:
                    print(f"  Zoomed region too short for nperseg={nperseg}, skipping.")
    except Exception as e:
        print(f"  ERROR: {e}")
    _step_times['6_spectrograms'] = _time.perf_counter() - _t0

    # ----------------------------------------------------------
    # DONE — TIMING REPORT
    # ----------------------------------------------------------
    elapsed = _time.perf_counter() - t_region_start
    print(f"\n  ⏱️  Batch Step Timing:")
    for step, secs in _step_times.items():
        print(f"    [{step:.<30s}] {secs:.2f}s")
    print(f"    [{'TOTAL':.<30s}] {elapsed:.2f}s")
    print(f"  Output: {region_dir}")


# ============================================================
#  MAIN
# ============================================================
if __name__ == '__main__':
    t_total = _time.perf_counter()

    regions = CANDIDATES if RUN_REGIONS == 'all' else [CANDIDATES[i] for i in RUN_REGIONS]

    for region in regions:
        run_region(region['label'], region['trange'])

    print(f"\n{'='*60}")
    print(f"  ALL DONE — {len(regions)} region(s) in {_time.perf_counter() - t_total:.1f}s")
    print(f"  Output root: {OUTPUT_ROOT}")
    print(f"{'='*60}")
