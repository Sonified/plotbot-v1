# Captain's Log — 2026-07-31

## v1.17 — HAM angular binning pipeline ported into plotbot-v1

Jaye asked how `ham_bin_data_plus_minus_3_days_corrected.json` (the file
behind multiplot's `ham_binned_degrees_overlay`) was created, wanting to
extend the rainbow plot's ham overlay to recent encounters. Srijan didn't
make the file — **we did**, in December 2025 in the main Plotbot repo
(commit `975a578`), implementing Srijan's binning method. The generator
never made it into plotbot-v1 with the v1.00 public release; only the
pre-baked JSON did. This session ports the whole pipeline so anyone
(read: Jaye) can regenerate and extend the file.

### The provenance story, reconstructed

- **Dec 3, 2025**: first generator (`ham_bin_generator_3day.py`) — used
  5-minute SPICE trajectory cadence as the occurrence-rate denominator,
  producing impossible `ham_frac > 1` values.
- **Dec 4, 2025**: corrected generator (`ham_bin_generator_correct.py`)
  follows Srijan's actual approach — interpolate the SPICE trajectory
  onto SPAN SPI L3 timestamps so the denominator is real SPAN
  measurement counts. Output renamed `_corrected.json`; flawed original
  kept as `_original.json`. Multiplot default path points at corrected.
- **April 10, 2026**: Jaye delivered `Hamstrings_E27/` for the vdrift
  work. Buried discovery of this session: that archive is a **complete
  HamPy rerun** — 189 daily CDFs spanning 2019-04-01 → 2026-03-11, not
  just E27. Only the 5 E27 files had been copied out at the time.

### What was built

**New: `ham_angular_binning/`** — self-contained pipeline folder:

- `ham_bin_generator.py` — ported from the archived original with real
  upgrades:
  - **SPICE-derived perihelion times** for E24+ (min heliocentric
    distance within the `get_encounter.py` window; two-pass hourly →
    1-minute search). Validated against E23's known perihelion: agrees
    within 1 minute. Computed: E24 = 2025/06/19 09:32, E25 = 2025/09/15
    20:22, E26 = 2025/12/13 07:11, E27 = 2026/03/11 18:17 (all 9.86 Rs).
  - **Three-tier SPAN timestamp sourcing**: local plotbot sf00 L3 CDFs →
    SPDF via pyspedas → Berkeley SWEAP server (interactive password
    prompt, downloads land in plotbot's local path).
  - **Auto-downloading SPICE kernels** (~330MB one-time, from SPDF/NAIF)
    into `data/psp/spice_data/` (gitignored).
  - **Merge semantics**: new encounters merge into the existing JSON
    instead of overwriting it, so partial runs are safe.
  - CLI: `python ham_angular_binning/ham_bin_generator.py 26 27`
- `README.md` — full provenance, method, data requirements, usage.

### Validation

- Syntax + imports verified in base anaconda env (`/opt/anaconda3/bin/python`).
- SPICE init + perihelion finder validated: recomputed E23's perihelion
  from the trajectory and it matched the known value within 1 minute.
- A full end-to-end E23 re-run (SPDF download path) was started but
  deliberately cancelled — the core binning functions (angular binning,
  ham counting, ham_frac formula) are verbatim from the Dec 2025
  original, and the data downloads are Jaye's to run.

### Data findings

- **E24 and E25 have no hamstring CDFs** — HamPy was never run for them.
  Post-E23 coverage: E26 = 2025-12-08 → 12-18, E27 = 2026-03-07 → 03-11.
- **E26/E27 SPI L3 not yet public at SPDF** — the generator must be run
  interactively so it can prompt for Berkeley SWEAP credentials.
- Full hamstring archive copied from `Hamstrings_E27/cdf/v02/` into
  `data/cdf_files/Hamstrings/` (gitignored, local).

### Infrastructure

- `.gitignore`: added `data/psp/spice_data/` (kernels are ~330MB).
- Memory saved: `ham-bin-json-provenance` in Claude project memory.

**Version tag**: `2026_07_31_v1.17`
**Commit message**: v1.17 Feature: HAM angular binning pipeline for extending the ham overlay JSON to new encounters
