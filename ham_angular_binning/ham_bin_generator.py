#!/usr/bin/env python
"""
Generate HAM angular bin JSON for the multiplot ham_binned_degrees_overlay.

This is the generator for:
    data/psp/ham_angular_bins/ham_bin_data_plus_minus_3_days_corrected.json

which multiplot reads (see plotbot/multiplot.py, ham_binned_degrees_overlay)
to draw the hammerhead occurrence-rate bar overlay on Carrington longitude
panels, in the style of Srijan's paper.

Method (Srijan's approach, implemented Dec 2025):
1. Load hammerhead detection times from HamPy CDFs (±3 days around perihelion)
2. Use pyspedas to get SPAN-I SPI L3 timestamps for the same window
   (downloads/caches the sf00 L3 moment files)
3. Interpolate the PSP SPICE trajectory onto the SPAN timestamps
4. Transform to Carrington coordinates, bin by 1 degree angular separation
5. Count ham detections vs total SPAN measurements per bin
6. ham_frac = ham_counts / (1 + all_counts)  -- always <= 1

Why "corrected"? The first version of this pipeline (Dec 3, 2025) used the
5-minute SPICE trajectory cadence as the denominator, which produced
impossible occurrence rates > 1. The corrected version (Dec 4, 2025) counts
actual SPAN measurements, matching Srijan's code.

Perihelion times: E04-E23 are hardcoded (matching plotbot/utils.py). For
newer encounters (E24+) the perihelion is computed directly from the SPICE
trajectory (minimum heliocentric distance within the encounter window), so
new encounters work as soon as their hamstring CDFs exist.

Data requirements (both gitignored -- see ham_angular_binning/README.md):
- data/psp/spice_data/       SPICE kernels (spp_nom_*.bsp, de430.bsp)
- data/cdf_files/Hamstrings/ HamPy CDFs (hamstring_YYYY-MM-DD_v02.cdf)

Usage:
    python ham_angular_binning/ham_bin_generator.py            # E04-E28
    python ham_angular_binning/ham_bin_generator.py 24 25 26   # specific encounters

Existing encounters in the output JSON are preserved: results are merged in,
so you can add new encounters without recomputing old ones.

Runtime: ~1-2 s per encounter once SPI L3 files are cached; first run on a
new encounter downloads ~6 days of SPI L3 moment CDFs via pyspedas.
"""

import sys
import os
import glob
import re
import json
import numpy as np
import cdflib
import cdflib.xarray
import xarray
import pandas as pd
from datetime import datetime
from astropy.time import Time
import astropy.units as u

# Repo root = parent of this script's directory
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

from sunpy.coordinates import spice, HeliographicCarrington
import pyspedas

SPICE_KERNEL_DIR = os.path.join(BASE_DIR, 'data', 'psp', 'spice_data')
HAMSTRING_DIR = os.path.join(BASE_DIR, 'data', 'cdf_files', 'Hamstrings')
JSON_OUTPUT = os.path.join(BASE_DIR, 'data', 'psp', 'ham_angular_bins',
                           'ham_bin_data_plus_minus_3_days_corrected.json')

# Known perihelion times (matches plotbot/utils.py PERIHELION_TIMES).
# Encounters not listed here get their perihelion computed from SPICE.
PERIHELION_TIMES = {
    4: '2020/01/29 09:37:00.000', 5: '2020/06/07 08:23:00.000',
    6: '2020/09/27 09:16:00.000', 7: '2021/01/17 17:40:00.000',
    8: '2021/04/29 08:48:00.000', 9: '2021/08/09 19:11:00.000',
    10: '2021/11/21 08:23:00.000', 11: '2022/02/25 15:38:00.000',
    12: '2022/06/01 22:51:00.000', 13: '2022/09/06 06:04:00.000',
    14: '2022/12/11 13:16:00.000', 15: '2023/03/17 20:30:00.000',
    16: '2023/06/22 03:46:00.000', 17: '2023/09/27 23:28:00.000',
    18: '2023/12/29 00:56:00.000', 19: '2024/03/30 02:21:00.000',
    20: '2024/06/30 03:47:00.000', 21: '2024/09/30 05:15:00.000',
    22: '2024/12/24 11:53:00.000', 23: '2025/03/22 22:42:00.000',
}

# Encounter date windows for SPICE perihelion search (matches
# plotbot/get_encounter.py). Extend this dict for future encounters.
ENCOUNTER_RANGES = {
    24: ('2025-05-06', '2025-08-01'),
    25: ('2025-08-02', '2025-10-28'),
    26: ('2025-10-29', '2026-01-12'),
    27: ('2026-01-13', '2026-04-15'),
    28: ('2026-04-16', '2026-07-15'),
}


# Public kernel sources (PSP predictive ephemeris through 2030 + planetary)
KERNEL_URLS = [
    'https://spdf.gsfc.nasa.gov/pub/data/psp/ephemeris/spice/ephemerides/spp_nom_20180812_20300101_v042_PostV7.bsp',
    'https://naif.jpl.nasa.gov/pub/naif/generic_kernels/spk/planets/de430.bsp',
]


def download_kernels():
    """Download the required SPICE kernels (~330MB total, one-time)."""
    import urllib.request
    os.makedirs(SPICE_KERNEL_DIR, exist_ok=True)
    for url in KERNEL_URLS:
        fname = url.split('/')[-1]
        dest = os.path.join(SPICE_KERNEL_DIR, fname)
        if os.path.exists(dest):
            continue
        print(f"  Downloading {fname} (large file, one-time)...")
        tmp = dest + '.part'
        urllib.request.urlretrieve(url, tmp)
        os.rename(tmp, dest)
        print(f"  Saved {dest}")


def init_spice():
    """Load SPICE kernels, downloading them first if missing."""
    kernel_files = sorted(glob.glob(os.path.join(SPICE_KERNEL_DIR, '*.bsp')))
    if not kernel_files:
        print(f"No SPICE kernels found in {SPICE_KERNEL_DIR} -- downloading...")
        download_kernels()
        kernel_files = sorted(glob.glob(os.path.join(SPICE_KERNEL_DIR, '*.bsp')))
    print(f"Loading {len(kernel_files)} SPICE kernel files...")
    spice.initialize(kernel_files)
    spice.install_frame('IAU_SUN')
    print("SPICE initialized")


def find_perihelion_from_spice(enc):
    """
    Compute perihelion time for an encounter by finding the minimum
    heliocentric distance of PSP within the encounter's date window.
    Two-pass: hourly scan over the full window, then 1-minute refinement.
    """
    if enc not in ENCOUNTER_RANGES:
        raise ValueError(
            f"E{enc:02d} has no entry in PERIHELION_TIMES or ENCOUNTER_RANGES. "
            f"Add its date window to ENCOUNTER_RANGES in this script.")

    start_str, end_str = ENCOUNTER_RANGES[enc]
    t0, t1 = Time(start_str), Time(end_str)

    # Pass 1: hourly
    n_hours = int((t1 - t0).to_value(u.hr))
    coarse = t0 + np.arange(n_hours) * u.hr
    traj = spice.get_body('SPP', coarse)
    dist = traj.transform_to(HeliographicCarrington(observer='self')).radius
    t_min = coarse[np.argmin(dist)]

    # Pass 2: 1-minute over +/- 2 hours
    fine = t_min + (np.arange(-120, 121) * u.min)
    traj = spice.get_body('SPP', fine)
    dist = traj.transform_to(HeliographicCarrington(observer='self')).radius
    peri_time = fine[np.argmin(dist)]
    peri_rs = dist.min().to_value(u.km) / 696000.0

    peri_str = peri_time.to_datetime().strftime('%Y/%m/%d %H:%M:%S.%f')[:-3]
    print(f"  E{enc:02d} perihelion from SPICE: {peri_str} ({peri_rs:.2f} Rs)")
    return peri_str


def get_perihelion(enc):
    """Known perihelion time if available, otherwise compute from SPICE."""
    if enc in PERIHELION_TIMES:
        return PERIHELION_TIMES[enc]
    return find_perihelion_from_spice(enc)


def datetime2unix(dt_arr):
    """Convert datetime-like array to unix timestamps."""
    if hasattr(dt_arr[0], 'timestamp'):
        return np.array([dt.timestamp() for dt in dt_arr])
    else:
        return pd.to_datetime(dt_arr).astype(np.int64) / 1e9


# Local plotbot SPI L3 proton moment files (downloaded by plotbot from
# Berkeley or SPDF). Used as the first source for SPAN timestamps.
SPI_SF00_LOCAL = os.path.join(BASE_DIR, 'data', 'psp', 'sweap', 'spi', 'l3',
                              'spi_sf00_l3_mom')
SPI_SF00_BERKELEY_URL = 'https://sprg.ssl.berkeley.edu/data/psp/data/sci/sweap/spi/L3/spi_sf00/'


def days_in_range(tstart, tend):
    """List of datetime64[D] days covering [tstart, tend]."""
    d0 = np.datetime64(tstart.strftime('%Y-%m-%d'))
    d1 = np.datetime64(tend.strftime('%Y-%m-%d'))
    return list(np.arange(d0, d1 + np.timedelta64(1, 'D')))


def find_local_spi_file(day):
    """Highest-version local sf00 L3 CDF for a given day, or None."""
    day_str = str(day).replace('-', '')
    year = str(day)[:4]
    pattern = os.path.join(SPI_SF00_LOCAL, year,
                           f'psp_swp_spi_sf00_[Ll]3_mom_{day_str}_v*.cdf')
    matches = sorted(glob.glob(pattern))
    return matches[-1] if matches else None


def download_spi_from_berkeley(day):
    """
    Download one day's sf00 L3 CDF from the Berkeley SWEAP server
    (password-protected; prompts once). Returns local path or None.
    """
    import requests
    from getpass import getpass

    if not sys.stdin.isatty():
        return None  # can't prompt for credentials non-interactively

    if not hasattr(download_spi_from_berkeley, '_auth'):
        print("    Berkeley SWEAP server credentials needed (unreleased data):")
        user = input("    Username: ")
        pw = getpass("    Password: ")
        download_spi_from_berkeley._auth = (user, pw)
    auth = download_spi_from_berkeley._auth

    year, month = str(day)[:4], str(day)[5:7]
    day_str = str(day).replace('-', '')
    index_url = f'{SPI_SF00_BERKELEY_URL}{year}/{month}/'
    try:
        r = requests.get(index_url, auth=auth, timeout=60)
        if r.status_code != 200:
            print(f"    Berkeley index fetch failed ({r.status_code}) for {index_url}")
            return None
        files = sorted(set(re.findall(
            rf'psp_swp_spi_sf00_L3_mom_{day_str}_v\d+\.cdf', r.text)))
        if not files:
            return None
        fname = files[-1]  # highest version
        out_dir = os.path.join(SPI_SF00_LOCAL, year)
        os.makedirs(out_dir, exist_ok=True)
        out_path = os.path.join(out_dir, fname)
        print(f"    Downloading {fname} from Berkeley...")
        with requests.get(index_url + fname, auth=auth, stream=True, timeout=300) as resp:
            resp.raise_for_status()
            with open(out_path, 'wb') as f:
                for chunk in resp.iter_content(chunk_size=1 << 20):
                    f.write(chunk)
        return out_path
    except Exception as e:
        print(f"    Berkeley download error for {day}: {e}")
        return None


def read_epochs_from_cdf(path):
    """Read the Epoch variable from a SPI L3 CDF as datetime64 array."""
    cdf = cdflib.CDF(path)
    epochs = cdf.varget('Epoch')
    return cdflib.epochs.CDFepoch.to_datetime(epochs)


def get_span_timestamps_pyspedas(tstart, tend):
    """SPAN timestamps via pyspedas/SPDF (public releases only)."""
    tstart_str = tstart.strftime('%Y-%m-%d/%H:%M:%S')
    tend_str = tend.strftime('%Y-%m-%d/%H:%M:%S')
    # sf0a matches the original Dec 2025 run that produced the corrected JSON.
    # (Timestamps are what matter here; sf00/sf0a share the same sweep cadence.)
    spi_vars = pyspedas.psp.spi(trange=[tstart_str, tend_str],
                                datatype='spi_sf0a_l3_mom', level='l3',
                                time_clip=True, notplot=True)
    if not spi_vars:
        return None

    spi_key = 'psp_spi_DENS' if 'psp_spi_DENS' in spi_vars else 'DENS'
    if spi_key not in spi_vars:
        spi_key = None
        for k in spi_vars.keys():
            if isinstance(spi_vars[k], dict) and 'x' in spi_vars[k]:
                spi_key = k
                break
        if spi_key is None:
            return None

    return spi_vars[spi_key]['x']


def get_span_timestamps(tstart, tend):
    """
    Get SPAN SPI L3 timestamps for [tstart, tend]. This is the key --
    we need SPAN cadence for a proper ham_frac denominator.

    Sources, in order:
    1. Local plotbot sf00 L3 CDFs (data/psp/sweap/spi/l3/spi_sf00_l3_mom/)
    2. SPDF via pyspedas (public releases; lags ~6 months)
    3. Berkeley SWEAP server (unreleased data; prompts for password)
    """
    print(f"    Getting SPI L3 timestamps {tstart} to {tend}...")
    days = days_in_range(tstart, tend)

    # Source 1: local plotbot files
    local_files = {d: find_local_spi_file(d) for d in days}
    missing = [d for d, f in local_files.items() if f is None]

    if missing:
        # Source 2: SPDF via pyspedas -- accept only if it covers the window
        dt_span = get_span_timestamps_pyspedas(tstart, tend)
        if dt_span is not None and len(dt_span) > 0:
            span0 = pd.Timestamp(np.asarray(dt_span)[0]).to_pydatetime().replace(tzinfo=None)
            span1 = pd.Timestamp(np.asarray(dt_span)[-1]).to_pydatetime().replace(tzinfo=None)
            from datetime import timedelta
            if (span0 - tstart) < timedelta(days=1) and (tend - span1) < timedelta(days=1):
                print(f"    Got {len(dt_span)} SPAN timestamps (SPDF/pyspedas)")
                return dt_span
            print(f"    SPDF data only covers {span0} to {span1} -- "
                  f"falling through to Berkeley")
        # Source 3: Berkeley (per missing day)
        print(f"    {len(missing)} day(s) not local/SPDF -- trying Berkeley server...")
        for d in missing:
            local_files[d] = download_spi_from_berkeley(d)

    available = [f for f in local_files.values() if f]
    if not available:
        return None

    got_days = [d for d, f in local_files.items() if f]
    if len(available) < len(days):
        print(f"    WARNING: SPI files for only {len(available)}/{len(days)} days")

    epochs = np.concatenate([read_epochs_from_cdf(f) for f in sorted(available)])
    epochs = np.sort(epochs)
    t0 = np.datetime64(tstart)
    t1 = np.datetime64(tend)
    epochs = epochs[(epochs >= t0) & (epochs <= t1)]
    print(f"    Got {len(epochs)} SPAN timestamps (local/Berkeley CDFs)")
    return epochs if len(epochs) else None


def get_trajectory_at_times(times):
    """Get SPICE trajectory at specific times, return in Carrington coords."""
    trajectory = spice.get_body('SPP', Time(times))
    traj_carr = trajectory.transform_to(HeliographicCarrington(observer='self'))
    return traj_carr


def bin_by_angular_separation(coords, max_sep_deg=1.0):
    """
    Bin coordinates by angular separation (Srijan's algorithm).
    Returns list of coordinate slices, one per bin.
    """
    lon = coords.lon.to_value(u.rad)
    lat = coords.lat.to_value(u.rad)
    valid = np.isfinite(lon) & np.isfinite(lat)
    n = len(lon)
    bins = []

    i = 0
    while i < n:
        if not valid[i]:
            i += 1
            continue
        j = i + 1
        while j < n and valid[j]:
            j += 1

        start = i
        while start < j:
            ref_lon, ref_lat = lon[start], lat[start]
            lon_block, lat_block = lon[start:j], lat[start:j]
            dlon, dlat = lon_block - ref_lon, lat_block - ref_lat
            sin_dlat2 = np.sin(dlat * 0.5)**2
            sin_dlon2 = np.sin(dlon * 0.5)**2
            a = sin_dlat2 + np.cos(ref_lat) * np.cos(lat_block) * sin_dlon2
            a = np.clip(a, 0.0, 1.0)
            angle_deg = np.rad2deg(2.0 * np.arcsin(np.sqrt(a)))
            too_far_idx = np.where(angle_deg > max_sep_deg)[0]
            end = j if too_far_idx.size == 0 else start + too_far_idx[0]
            bins.append(coords[start:end])
            start = end
        i = j

    return bins


def count_ham_in_bins(hammertimes, bins):
    """Count ham detections and total SPAN measurements per bin."""
    hammer_unix = datetime2unix(hammertimes)
    bin_start_unix = np.array([b.obstime[0].to_datetime().timestamp() for b in bins])
    bin_end_unix = np.array([b.obstime[-1].to_datetime().timestamp() for b in bins])

    left_idx = np.searchsorted(hammer_unix, bin_start_unix, side='left')
    right_idx = np.searchsorted(hammer_unix, bin_end_unix, side='right')
    ham_counts = right_idx - left_idx

    # all_counts = number of SPAN measurements in each bin (same cadence as ham!)
    all_counts = np.array([len(b) for b in bins])

    return ham_counts, all_counts


def load_ham_data(peri_str, num_days=3):
    """Load hamstring CDF data for +/- num_days around a perihelion."""
    peri_dt = datetime.strptime(peri_str, '%Y/%m/%d %H:%M:%S.%f')
    pday = np.datetime64(peri_dt).astype('datetime64[D]')
    enc_days = np.arange(pday - np.timedelta64(num_days, 'D'),
                         pday + np.timedelta64(num_days + 1, 'D'))

    filenames = [f for f in os.listdir(HAMSTRING_DIR) if f.startswith('hamstring_')]
    filedates = {np.datetime64(re.split('[_]', f)[1]).astype('datetime64[D]'): f
                 for f in filenames}

    xrs = []
    for day in enc_days:
        day_d = day.astype('datetime64[D]')
        if day_d in filedates:
            xrs.append(cdflib.xarray.cdf_to_xarray(
                os.path.join(HAMSTRING_DIR, filedates[day_d])))

    if not xrs:
        return None, None

    hamdata = xarray.concat(xrs, dim='record0')
    hammertimes = list(pd.to_datetime(hamdata['epoch'].data).to_pydatetime())
    return hamdata, hammertimes


def process_encounter(enc, num_days=3):
    """Process one encounter. Returns (result_dict, peri_str) or (None, peri_str)."""
    peri_str = get_perihelion(enc)

    print(f"  Loading ham data...")
    hamdata, hammertimes = load_ham_data(peri_str, num_days)
    if not hammertimes:
        return None, peri_str
    print(f"  {len(hammertimes)} ham detections")

    tstart, tend = hammertimes[0], hammertimes[-1]

    # KEY: Get SPAN timestamps from SPI L3 (local CDFs / SPDF / Berkeley)
    span_times = get_span_timestamps(tstart, tend)
    if span_times is None:
        print(f"  No SPI L3 data available for this window -- "
              f"run interactively with Berkeley credentials, or download "
              f"sf00 L3 CDFs into {SPI_SF00_LOCAL}")
        return None, peri_str
    print(f"  {len(span_times)} SPAN measurements")

    # Get trajectory at SPAN timestamps (same cadence!)
    print(f"  Getting trajectory at SPAN times...")
    traj_carr = get_trajectory_at_times(span_times)

    # Bin by angular separation
    print(f"  Binning by angular separation...")
    bins = bin_by_angular_separation(traj_carr, max_sep_deg=1.0)
    print(f"  {len(bins)} bins")

    # Count ham detections and SPAN measurements per bin
    ham_counts, all_counts = count_ham_in_bins(hammertimes, bins)
    ham_frac = ham_counts / (1 + all_counts)

    max_frac = np.max(ham_frac)
    print(f"  Max ham_frac: {max_frac:.4f} (should be <= 1)")
    if max_frac > 1:
        print(f"  WARNING: ham_frac > 1 detected!")

    start_lons = np.array([b[0].lon.to_value(u.deg) for b in bins])
    end_lons = np.array([b[-1].lon.to_value(u.deg) for b in bins])

    return {
        'bins': bins,
        'ham_frac': ham_frac,
        'ham_counts': ham_counts,
        'all_counts': all_counts,
        'start_lons': start_lons,
        'end_lons': end_lons,
        'n_detections': len(hammertimes),
        'n_span_measurements': len(span_times),
    }, peri_str


def save_to_json(encounters, output_path, num_days=3):
    """Process encounters and merge results into the output JSON."""
    # Merge into existing JSON so partial runs don't lose old encounters
    all_data = {}
    if os.path.exists(output_path):
        with open(output_path, 'r') as f:
            all_data = json.load(f)
        print(f"Loaded existing JSON with {len(all_data)} encounters "
              f"(new results will be merged in)")

    print(f"Processing {len(encounters)} encounters...")

    for enc in encounters:
        enc_str = f'E{enc:02d}' if enc < 10 else f'E{enc}'
        print(f"\n{'='*60}")
        print(f"Processing {enc_str}...")
        print(f"{'='*60}")

        try:
            result, peri_str = process_encounter(enc, num_days)
        except ValueError as e:
            print(f"  SKIPPED: {e}")
            continue

        if not result:
            print(f"  No hamstring data for {enc_str} "
                  f"(need CDFs within +/-{num_days} days of {peri_str})")
            continue

        bins_list = [{
            'start_lon': float(result['start_lons'][i]),
            'end_lon': float(result['end_lons'][i]),
            'ham_frac': float(result['ham_frac'][i]),
            'ham_count': int(result['ham_counts'][i]),
            'all_count': int(result['all_counts'][i])
        } for i in range(len(result['bins']))]

        all_data[enc_str] = {
            'n_bins': len(result['bins']),
            'n_detections': result['n_detections'],
            'n_span_measurements': result['n_span_measurements'],
            'perihelion': peri_str,
            'window_days': num_days,
            'bins': bins_list
        }

    # Keep encounters sorted in the output
    all_data = dict(sorted(all_data.items()))

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(all_data, f, indent=2)
    print(f"\n{'='*60}")
    print(f"Saved {len(all_data)} encounters to: {output_path}")
    print(f"{'='*60}")


if __name__ == '__main__':
    if len(sys.argv) > 1:
        encounters = [int(a.lstrip('Ee')) for a in sys.argv[1:]]
    else:
        max_enc = max(list(PERIHELION_TIMES) + list(ENCOUNTER_RANGES))
        encounters = list(range(4, max_enc + 1))

    init_spice()
    save_to_json(encounters, JSON_OUTPUT, num_days=3)
