# Updating the Ham Overlay JSON for New Encounters

**Audience:** Jaye (or an AI agent working on Jaye's behalf).
**Goal:** Extend `data/psp/ham_angular_bins/ham_bin_data_plus_minus_3_days_corrected.json`
— the file multiplot's `ham_binned_degrees_overlay` reads — to include recent
encounters (E26, E27, and future ones), matching the style of Srijan's paper figure.

## Background (30 seconds)

This JSON was created by Robert (Dec 2025), implementing the angular binning
method from Srijan's paper code. It caches hammerhead occurrence rates binned by
~1° of Carrington longitude, ±3 days around each perihelion, so multiplot renders
instantly. It currently covers E04–E23. The generator that makes it is in this
folder: `ham_bin_generator.py`. Full provenance and method details: `README.md`.

## Prerequisites

1. **Python environment** with: `sunpy` (with spiceypy support), `pyspedas`,
   `cdflib`, `xarray`, `astropy`, `scipy`, `pandas`, `requests`.
   Any env that runs HamPy + sunpy likely works. Quick check:
   ```bash
   python -c "from sunpy.coordinates import spice; import pyspedas, cdflib, xarray; print('OK')"
   ```

2. **Hamstring CDFs** (HamPy output, `hamstring_YYYY-MM-DD_v02.cdf`, one per day)
   placed in `data/cdf_files/Hamstrings/` (gitignored — create it if needed).
   The generator needs files within ±3 days of each target perihelion.
   - E26 needs 2025-12-10 → 2025-12-16 (perihelion 2025/12/13 07:11)
   - E27 needs 2026-03-08 → 2026-03-14 (perihelion 2026/03/11 18:17)
   - **E24 and E25 have no HamPy output as of July 2026** — if you want them on
     the plot, run HamPy for windows around 2025/06/19 09:32 (E24) and
     2025/09/15 20:22 (E25) first, then include them in the run below.

3. **Berkeley SWEAP credentials.** E26/E27 SPI L3 moment data is not yet public
   at SPDF, and the occurrence-rate denominator needs the SPAN measurement
   timestamps. The script will prompt for the SWEAP username/password and
   download what it needs from `sprg.ssl.berkeley.edu`. **Run in an interactive
   terminal** so the prompt can appear. (For E04–E23-era reruns, public SPDF
   data is used automatically and no credentials are needed.)

4. **SPICE kernels: nothing to do** — the script auto-downloads them (~330MB,
   one-time) into `data/psp/spice_data/` from public SPDF/NAIF URLs.

## The one command

From the repo root:

```bash
python ham_angular_binning/ham_bin_generator.py 26 27
```

That's it. The script:
- computes each encounter's perihelion directly from the SPICE trajectory
  (no hardcoded dates needed for new encounters),
- loads ham detections from your hamstring CDFs,
- fetches SPAN timestamps (local plotbot CDFs → SPDF → Berkeley, in that order),
- bins by 1° angular separation and computes `ham_frac = ham_count / (1 + all_count)`,
- **merges** the new encounters into the existing JSON — E04–E23 are preserved
  untouched. Safe to re-run; each run just overwrites the encounters you name.

Runtime: seconds per encounter once data is downloaded.

## Verify it worked

1. The console prints `Max ham_frac: <value> (should be <= 1)` per encounter —
   confirm it is ≤ 1.
2. Check the JSON now contains the new keys:
   ```bash
   python -c "import json; print(sorted(json.load(open('data/psp/ham_angular_bins/ham_bin_data_plus_minus_3_days_corrected.json')).keys()))"
   ```
3. Plot it — multiplot picks the file up automatically. In any multiplot with
   `use_degrees_from_perihelion` on an E26/E27 time range, set:
   ```python
   plt.options.ham_binned_degrees_overlay = True
   ```
   The steelblue occurrence-rate bars should appear on the new panels.

## Adding future encounters (E29+)

1. Add the encounter's date window to `ENCOUNTER_RANGES` in
   `ham_bin_generator.py` (mirror the entry in `plotbot/get_encounter.py`).
2. Drop that encounter's hamstring CDFs into `data/cdf_files/Hamstrings/`.
3. Run the generator with the new encounter number.

## Troubleshooting

- **"No hamstring data for EXX"** — no `hamstring_*.cdf` files within ±3 days of
  the perihelion printed on the line above. Check filenames/dates in
  `data/cdf_files/Hamstrings/`.
- **"No SPI L3 data available for this window"** — the run was non-interactive
  (couldn't prompt for Berkeley credentials) or the credentials failed. Run in a
  regular terminal. Alternatively, manually place daily
  `psp_swp_spi_sf00_L3_mom_YYYYMMDD_v*.cdf` files into
  `data/psp/sweap/spi/l3/spi_sf00_l3_mom/<YEAR>/` and re-run.
- **`ham_frac > 1` warning** — should never happen (that bug is why this file
  has "corrected" in its name — see README.md). If it appears, something is
  wrong with the SPAN timestamp source; tell Robert.
- **Kernel download fails** — grab the two files listed under `KERNEL_URLS` at
  the top of `ham_bin_generator.py` manually and put them in
  `data/psp/spice_data/`.

## Sanity anchor

This exact pipeline was validated July 2026 by re-running E23 from scratch:
output was byte-identical to the existing JSON entry, and the SPICE-computed
perihelion matched the known E23 time within 1 minute.
