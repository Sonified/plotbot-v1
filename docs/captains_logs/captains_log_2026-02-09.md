# Captain's Log - 2026-02-09

## v1.01 Bugfix: Apply audifier fixes from v3.81

### Summary
Applied three critical audifier fixes that were previously implemented in v3.81:
1. Added `__setattr__` method to `_LazyAudifier` class to enable property assignment
2. Fixed typo in time clipping check (`plot_options` → `plot_config`)
3. Fixed directory navigation button to use `output_dir` instead of `self.save_dir`

### Files Changed
- `plotbot/__init__.py`: Added `__setattr__` to `_LazyAudifier` class (line 275)
- `plotbot/audifier.py`:
  - Fixed `hasattr` check from `plot_options` to `plot_config` (line 176)
  - Fixed directory button to use `output_dir` (line 635)

### Context
These fixes ensure audifier works correctly with lazy loading and proper time range clipping. The fixes maintain consistency between the v1 and v3.81 codebases.
