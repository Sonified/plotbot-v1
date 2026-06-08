# Captain's Log -- 2026-06-08

## v1.12 -- Self-contained Magnetic Hole Finder notebook: settings-to-scatter pipeline

The big goal: change settings at the top, Run All, and have everything flow through automatically -- detection uses the settings, writes a new marker file, and all downstream showda_holes scatter plots use that new marker file.

### The pipeline problem

Previously the notebook had detection cells AFTER the scatter plot cells, and all marker file paths were hardcoded. Changing `HoleFinderSettings` had zero effect on the plots because `showda_holes` reads from marker files, not from settings objects. The scatter plots were always reading the same old file regardless of what you tuned.

### Restructured notebook flow

Reorganized for clean top-to-bottom execution:

1. **Settings cell** (`HoleFinderSettings`) -- standard profile with commented conservative overrides
2. **Detection cell** -- runs `detect_magnetic_holes_and_generate_outputs()`, auto-captures the new marker file path
3. **Scatter plot cells** -- all reference `trange` and `mh_marker_file_path` from above, no hardcoded paths

### Core changes

- **`magnetic_hole_finder_core.py`**: `detect_magnetic_holes_and_generate_outputs()` now returns 8-tuple (added `marker_file_path` as 8th value). Wired through `output_magnetic_holes()` return value.
- **`MH_format_output.py`**: `output_magnetic_holes()` now returns the file path it wrote. Fixed double-nested output directory bug (was calling `setup_output_directory` twice -- once in core.py, once in format_output.py).
- **`data_management.py`**: Fixed import ordering issue -- module-level plotbot import fails at startup because plotbot isn't fully initialized yet. Added lazy re-import inside `download_and_prepare_high_res_mag_data()` that retries at call time. Silenced the harmless startup warning.
- **`plotbot/showda_holes.py`**: Extended multi-panel support from max 4 to max 10 panels. Fixed unused-axes hiding to work with any grid size.

### Settings profiles

Standard profile (current defaults): permissive, break only for shallow holes. 85 holes found in E17 06:32-06:45.

Conservative overrides (commented, ready to uncomment): tighter depth threshold (0.40), reject complex/asymmetric/wide-angle holes. For Jaye's stricter methodology.

Bump `MARKER_FILE_VERSION` to preserve old runs when testing new settings.

### Files touched

- `plotbot/__init__.py` -- version v1.12
- `example_notebooks/Magnetic_Hole_Finder.ipynb` -- restructured for Run All flow
- `magnetic_hole_finder/magnetic_hole_finder_core.py` -- 8-tuple return with marker path
- `magnetic_hole_finder/MH_format_output.py` -- return file path, fix double-nesting
- `magnetic_hole_finder/data_management.py` -- lazy imports, silence warning
- `plotbot/showda_holes.py` -- support up to 10 panels

### Next session

Goal: take the newly self-contained notebook to a different encounter and see what we find. E17 has been the test bed -- time to point the pipeline at E9, E10, E11, E15, or something entirely new and let the hole finder loose. Just change `trange` at the top, Run All, and explore. The time range definitions are already in the detection cell, ready to swap.
