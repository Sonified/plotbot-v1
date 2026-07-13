# Captain's Log -- 2026-06-15

## v1.13 -- Holey Grail batch scan pipeline, FFT spectrogram, hodogram fixes

### The Holey Grail

Built `the_holey_grail/batch_scan.py` -- a batch pipeline that scans Jaye's 5 starred magnetic hole candidate time regions through the full plotbot pipeline. Per region it generates:

- Hole detection (marker file, audio WAVs, iZotope markers)
- Low-res 4-panel and high-res 8-panel hodograms (showda_holes)
- Full-range and zoomed time series
- Clustered zoom views (intelligent gap-based clustering, targets 5 groups)
- FFT spectrograms at 3 resolutions (8192, 16384, 32768) -- full and zoomed, raw and composite (|B| overlay)
- Enriched run_settings.json with data source, CDF file names, cadence

5 target regions: E15 (12hr, 1060 holes!), E21 x3, E23. All 5 run in ~6 minutes with warm cache.

### FFT Spectrogram (replaced CWT)

`magnetic_hole_finder/wavelet_scalogram.py` completely rewritten from CWT to `scipy.signal.spectrogram`. 200x speedup (6.9s to 0.035s for 2.1M samples). Auto color scaling: `vmin = median - 2.5*std`, `vmax = median + 6*std` on dB values with linear colormap.

### Hodogram fixes

- **Z-ordering**: Outside points draw first (zorder=1), inside on top (zorder=2), min dots topmost (zorder=3). Previously all in one scatter call -- inside points were buried under thousands of outside points.
- **Min point styling**: Bright yellow (#FFFF00), 40% of original size, black outline, full opacity. Pops against red/blue.
- **In-point visibility**: 70% opacity, proper layering.

### Stale cache bug

When batch-processing multiple regions, showda_holes checked `datetime_array is not None` to skip data loading. After region 1 loaded data, region 2 saw stale data and skipped reload. Fix: explicit `get_data()` call for all instruments at the start of each region.

### .env credentials

Added `the_holey_grail/.env` for Jaye's restricted PSP SWEAP credentials. Batch scan auto-loads and sets `server_access.session.auth` to bypass the interactive getpass prompt.

### v1.14 -- Added Holey Grail output to repo

Un-ignored `the_holey_grail/E*/` directories so batch scan output (images, audio, run_settings) is tracked in the repo. 5 event regions, 135 files, ~261 MB of hodograms, time series, spectrograms, WAV audio, and marker files.

### Cadence discovery

Investigated missing hodogram in-points. Root cause: standard epad (3.5s) and proton (1.75s) cadences are too slow to resolve sub-second holes. HR instruments (proton_hr at 0.22s, epad_hr at 0.87s) capture 4-5 samples per hole. The 4-panel standard plots will inherently have sparse in-points -- it's physics, not a bug.
