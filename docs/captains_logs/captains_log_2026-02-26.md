# Captain's Log - 2026-02-26

## v1.04 Bugfix: Fix y_limit on custom variables, pyspedas 2.x compat, installer v1 naming

### Custom Variable y_limit Fix
- **Bug:** Setting style attributes (like `y_limit`) on a custom variable between plot calls was silently dropped
- **Root cause:** Every `plotbot()` call evaluates the lambda and creates a fresh internal data object. The user's Python variable still pointed to the old object, so attributes set on it were invisible to the next plot call
- **Fix:** `plotbot()` now stores the user's actual variable reference in `plot_requests` and syncs style attributes from it onto the fresh internal copy before plotting. Two small changes in `plotbot_main.py` — store `original_var_ref`, then sync styles in plot prep

### pyspedas 2.x Compatibility
- **Bug:** pyspedas 2.1.0 (installed in new micromamba env) removed top-level mission shortcuts (`pyspedas.psp`, `pyspedas.wind`). They now live under `pyspedas.projects`
- **Fix:** Added compatibility shim at all 4 `import pyspedas` locations that aliases mission modules from `pyspedas.projects` if the top-level shortcut doesn't exist. Works with both pyspedas 1.x and 2.x

### Installer v1 Naming
- Renamed all environments and kernels: `plotbot_anaconda` -> `plotbot_v1_anaconda`, `plotbot_micromamba` -> `plotbot_v1_micromamba`
- Display names: "Plotbot v1 (Anaconda)" and "Plotbot v1 (Micromamba)"
- Fixed smart Homebrew detection to prevent duplicate installations
- Fixed smart micromamba path detection across all scripts
- Suppressed micromamba subprocess stderr spam

### Files Changed
- `plotbot/plotbot_main.py`: y_limit fix (store original_var_ref, sync styles)
- `plotbot/data_download_pyspedas.py`: pyspedas 2.x shim (2 locations)
- `plotbot/vdyes.py`: pyspedas 2.x shim
- `plotbot/plotbot_interactive_vdf.py`: pyspedas 2.x shim
- `plotbot/data_classes/custom_variables.py`: removed debug prints
- `plotbot/__init__.py`: removed debug prints, version bump
- `environment.yml`, `environment.cf.yml`: v1 naming
- `install_scripts/*`: v1 naming, smart Homebrew/micromamba detection, stderr suppression
