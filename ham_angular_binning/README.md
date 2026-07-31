# HAM Angular Binning

Generator for the pre-computed hammerhead occurrence-rate data used by
multiplot's `ham_binned_degrees_overlay` option (the Srijan-paper-style
bar overlay on Carrington longitude panels).

**Output:** `data/psp/ham_angular_bins/ham_bin_data_plus_minus_3_days_corrected.json`

**Consumer:** `plotbot/multiplot.py` (search for `ham_binned_degrees_overlay`)

## Provenance

This file was created by Robert Alexander (with Claude) in December 2025,
implementing the binning method from Srijan's paper code. It is a
pre-computed cache: computing occurrence rates live takes ~17 s per run
(SPICE trajectory + CDF loading + binning across all encounters), while
reading the JSON is sub-second.

**Why "corrected"?** The first version (Dec 3, 2025) used the 5-minute
SPICE trajectory cadence as the denominator of the occurrence rate, which
produced impossible values (ham_frac > 1). The corrected version
(Dec 4, 2025) follows Srijan's actual approach: interpolate the SPICE
trajectory onto the SPAN-I SPI L3 timestamps, so the denominator is real
SPAN measurement counts and `ham_frac = ham_count / (1 + all_count)` is
always <= 1. The flawed file is kept as
`ham_bin_data_plus_minus_3_days_original.json` for reference.

## Method

For each encounter (±3 days around perihelion):

1. Load hammerhead detection times from HamPy CDFs
2. Get SPAN-I SPI L3 timestamps via pyspedas (downloads/caches)
3. Interpolate PSP SPICE trajectory onto the SPAN timestamps
4. Transform to Heliographic Carrington coordinates
5. Walk the trajectory, grouping points into bins of < 1° angular separation
6. Count ham detections and SPAN measurements per bin
7. `ham_frac = ham_count / (1 + all_count)`

Perihelion times for E04–E23 are hardcoded (matching
`plotbot/utils.py`). For E24 onward the perihelion is computed directly
from the SPICE trajectory (minimum heliocentric distance within the
encounter window from `plotbot/get_encounter.py` ranges), so new
encounters work automatically once their hamstring CDFs are available.

## Data requirements (gitignored — set up locally)

| Data | Location | Source |
|------|----------|--------|
| SPICE kernels | `data/psp/spice_data/` | **Auto-downloaded on first run** (~330MB): `spp_nom_20180812_20300101_v042_PostV7.bsp` (PSP ephemeris through 2030, from [SPDF](https://spdf.gsfc.nasa.gov/pub/data/psp/ephemeris/spice/ephemerides/)) + `de430.bsp` (from [NAIF](https://naif.jpl.nasa.gov/pub/naif/generic_kernels/spk/planets/)) |
| Hamstring CDFs | `data/cdf_files/Hamstrings/` | HamPy output, `hamstring_YYYY-MM-DD_v02.cdf` (one per day). Full archive 2019-04-01 → 2026-03-11 also lives in `Hamstrings_E27/cdf/v02/` (delivered by Jaye April 2026 with the vdrift work) |
| SPI L3 timestamps | three-tier fallback | (1) local plotbot CDFs in `data/psp/sweap/spi/l3/spi_sf00_l3_mom/`, (2) SPDF via pyspedas (public releases, ~6-month lag), (3) Berkeley SWEAP server (unreleased data; prompts for the SWEAP password, downloads land in the plotbot local path) |

### Hamstring archive coverage note

The HamPy archive has gaps: **E24 (Jun 2025) and E25 (Sep 2025) have no
hamstring CDFs** — HamPy was not run for those encounters. Coverage after
E23: E26 = 2025-12-08 → 12-18, E27 = 2026-03-07 → 03-11. If E24/E25 CDFs
are ever produced, just drop them in `data/cdf_files/Hamstrings/` and
rerun.

Recent encounters (E26/E27) also need SPI L3 data that is not yet at SPDF,
so run the generator **interactively** for those — it will ask for the
Berkeley SWEAP credentials.

## Usage

```bash
# All encounters E04 through the latest defined (skips any without ham CDFs)
python ham_angular_binning/ham_bin_generator.py

# Just specific encounters (merged into the existing JSON, others preserved)
python ham_angular_binning/ham_bin_generator.py 24 25 26 27
```

Environment needs: `sunpy` (with spiceypy support), `pyspedas`, `cdflib`,
`xarray`, `astropy`, `scipy`. On Robert's machine the base anaconda env
has all of these: `/opt/anaconda3/bin/python`.

## Adding future encounters

1. Add the encounter date window to `ENCOUNTER_RANGES` in
   `ham_bin_generator.py` (mirror `plotbot/get_encounter.py`)
2. Drop the new hamstring CDFs into `data/cdf_files/Hamstrings/`
3. Run the generator for that encounter — done

## History

- Original exploration and first generator: main Plotbot repo,
  `tests/archive/scripts/ham_bin_generator_3day.py` and
  `ham_bin_generator_correct.py` (commit `975a578`, Dec 4, 2025)
- Captain's log: `docs/captains_logs/captains_log_2025-12-03.md`
