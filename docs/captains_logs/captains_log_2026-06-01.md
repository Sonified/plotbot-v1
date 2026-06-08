# Captain's Log -- 2026-06-01

## v1.10-v1.11 -- Magnetic Hole Finder: Parker Four conference images recovered + high-res showda_holes cell

Session started with Robert searching for the "amazing" 2x2 correlation plots he'd made for the Parker Solar Probe 4 conference -- magnetic holes with brazil plots and multi-panel scatter comparisons. The plots had been generated months earlier but the trail was cold.

### The archaeology

Traced the work back through both repos:

- **plotbot-v1**: Had `Magnetic_Hole_Finder.ipynb` in `example_notebooks/` and the core detection code in `magnetic_hole_finder/`, but the output images were gitignored and only existed locally in the old v1.0 repo.
- **Plotbot v1.0** (`/GitHub/Plotbot/`): The motherlode. `magnetic_hole_finder/MH_Images/` contained 6 Parker Four conference images (1.2 MB total), all gitignored and never pushed. The original code was tagged at v2.27 (May 7, 2025) on the `data_cubby_refactor` branch.

**Key images recovered:**
- `17_Centroids.png` -- E17 2x2: |B| vs Centroids, Anisotropy, Temperature, Pressure (wider time range)
- `E17_9_28.png` -- E17 2x2: same layout, tighter 06:32-06:45 window
- `E15Multipanel.png` -- E15 2x2 correlation layout
- `E15_2_med.png` / `E15_closer.png` -- E15 |B| time series with detected holes at two zoom levels
- `THEEDGE.png` -- Multi-panel derivative analysis with smoothing windows

### v1.10 -- Conference images into plotbot-v1

Copied all 6 images from `/GitHub/Plotbot/magnetic_hole_finder/MH_Images/` into `plotbot-v1/magnetic_hole_finder/MH_Images/`. Removed the `MH_Images/` entry from `.gitignore` so they'd actually be tracked this time.

### The cadence discovery

Robert asked a sharp question: what resolution data is the notebook actually using? Traced the pipeline:

```
magnetic_hole_finder_core.py  -->  marker .txt files  -->  showda_holes.py  -->  2x2 plots
         (find holes)              (hole boundaries)      (plot correlations)
```

`showda_holes.py` is completely data-agnostic -- it plots whatever you hand it. The cadence choice lives entirely in the notebook cell. The existing cell was using:

- **Proton**: `proton` -- standard cadence (`spi_sf00_l3_mom`, ~0.87-3.5s)
- **Electron/Strahl**: `epad` -- survey cadence (`spe_sf0_pad`, ~28s!!)
- **Mag**: `mag_rtn_4sa` -- 4 samples/sec (~0.25s)

Jaye flagged that 28s for strahl was way too slow -- the high-res product should be sub-second. He was right: `epad_hr` uses `spe_af0_pad` (SPAN-E archive full cadence). The upper-left EPAD centroids panel in the original 17_Centroids.png only had ~112 points because of the 28s survey cadence driving the resampling.

### v1.11 -- High-res showda_holes cell

Added a new cell to `Magnetic_Hole_Finder.ipynb` (kept the standard-cadence cell intact for comparison) that swaps in:

- `epad_hr.centroids` (sub-second strahl, `spe_af0_pad`)
- `proton_hr.anisotropy / t_par / t_perp` (high-res proton moments, `spi_af00_L3_mom`)
- `mag_rtn_4sa.bmag` (unchanged, already fast)

The cell also saves output to `Example_Images/E17_showda_holes_HR.png` at 150 DPI.

### pytplot dependency fix

Running the notebook hit a `ModuleNotFoundError` for `pytplot` -- the `magnetic_hole_finder/data_management.py` imports it at the top level. The original `pytplot` package is broken with bokeh 3.x (import path changes). Fixed by installing `pytplot-mpl-temp` (the maintained matplotlib-based fork, same module name) and adding `pytplot-mpl-temp>=2.0` to `requirements.txt`.

### Architecture note for future reference

The two-piece pipeline is important to keep straight:
- `magnetic_hole_finder_core.py` **detects** holes and writes marker `.txt` files. Needs pytplot/pyspedas for raw mag data download.
- `showda_holes.py` **plots** 2x2 correlation panels using those marker files. Completely agnostic to data resolution -- just takes whatever plotbot data objects you hand it and resamples the faster instrument to match the slower one via nearest-neighbor snapping.

The `showda_holes` resampling logic (lines 244-289) picks `target_dt = max(x_cadence, y_cadence)`, builds a common time grid at the slower cadence, and `reindex(method='nearest')` both series onto it. No interpolation. Higher-cadence data gets decimated to match. For scatter plots this is the right call.

### Files touched

- `plotbot/__init__.py` -- version bumps to v1.10 and v1.11
- `example_notebooks/Magnetic_Hole_Finder.ipynb` -- new high-res showda_holes cell
- `magnetic_hole_finder/MH_Images/` -- 6 Parker Four conference images added
- `.gitignore` -- removed MH_Images exclusion
- `requirements.txt` -- added `pytplot-mpl-temp>=2.0`
- `Example_Images/E17_showda_holes_HR.png` -- high-res output saved
