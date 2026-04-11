# Captain's Log — 2026-04-10

## v1.06 — E27 Spectral Correlation Notebook

Added a new exploratory notebook: `example_notebooks/spectral_correlation_e27.ipynb`.

### What it does
Tests the hypothesis that ion cyclotron waves drive hammerhead formation in PSP SPAN-I proton velocity distributions. Correlates B_N power spectral density above a tunable cutoff frequency against three hammerhead observables:

1. **Hamogram (occurrence rate)** — hammerhead detection count per bin
2. **n_ham / n_core** — fraction of the proton population in the hammerhead state
3. **Tperp_ham / Tpar_ham** — temperature anisotropy of the hammerhead population

Time window: `2026/03/11 07:10–08:30 UT` (E27 perihelion approach).

### Key design choices
- **Single split point** (`f_cutoff = 10 Hz`) divides the spectrum into two disjoint regions:
  - Above cutoff = target (cyclotron-resonant range)
  - Below cutoff = disjoint control
- **Kolmogorov roll-off argument** justifies extending the above-cutoff band to Nyquist — power rolls off so hard above ~50 Hz that including those bins is cosmetic.
- **Native 120-second binning** for all three targets (`bin_sec = 120`, `use_single_bin = True`) instead of rolling-mean smoothing. Gives ~40 fully independent samples per target. Honest p-values straight from scipy — no effective-n bookkeeping needed.
- **Per-target bin-size overrides** available when `use_single_bin = False` (per-hamogram, per-n_ham, per-anisotropy).

### Pipeline structure
- **Step 1**: load `mag_rtn.bn`, `ham.n_ham`, `ham.n_core`, `ham.Tperp_ham`, `ham.Tpar_ham` + binning config
- **Step 2**: B_N spectrogram (10 s windows, ~0.1 Hz resolution, NaN-interpolated to prevent blank bands)
- **Step 3**: 5-panel overview (B_N, spectrogram, n_ham/n_core, Tperp/Tpar, hamogram) + native binning of all three per-detection targets with NaN fill across empty bins
- **Step 3b**: split-point tuning cell with horizontal line overlay
- **Step 4**: per-detection correlations (n_ham/n_core and Tperp/Tpar) on the 120 s grid
- **Step 5**: hamogram-specific correlation (30 s → 120 s rebin) with side-by-side above/below cutoff scatter plots
- **Step 6**: sanity-check table comparing all three targets × (above, below) cutoff
- **Step 7**: full diagnostic with Pearson / log-Pearson / log-log / Spearman columns and honest p-values
- **Step 8**: 30 s (now 120 s) binned overlay plot
- **Step 9**: dynamic paper-ready findings printout
- **Notes cell**: markdown write-up of caveats (smoothing tradeoffs, Pearson vs log-Pearson vs log-log vs Spearman, band-tuning caveat, effective-n, next steps)

### Results so far (E27 perihelion)
- **Hamogram (formation rate)**: log-Pearson r ≈ +0.65, Spearman r ≈ +0.76, p ≈ 10⁻⁸ at n = 40 fully independent 120 s bins. Below-cutoff control ≈ 0. Band-specific, bulletproof.
- **n_ham / n_core (fraction)**: weaker positive correlation, Spearman ~+0.36 to +0.51. Tentative.
- **Tperp / Tpar (anisotropy)**: weak negative hint. Uncertain whether real self-regulation or trajectory drift — detrending would settle it.

### Infrastructure changes beyond the notebook
- `plotbot/__init__.py`: version bumped to v1.06
- `.gitignore`: added `Hamstrings_E27/` so the E27 source archive stays local-only
- E27 CDF files copied into `data/cdf_files/Hamstrings/` so plotbot's existing ham handler picks them up automatically
- `example_notebooks/plotbot_audification_examples.ipynb`: unrelated pending updates also included in this push

### Gotchas worth remembering
- `scipy.ndimage.uniform_filter1d` has a cumulative-sum internal implementation — a single NaN input poisons every subsequent output. Always NaN-interpolate before smoothing.
- When correlating count data (hamogram) with log-normal quantities (band power), `log-Pearson` (log x vs linear y) is the right metric. For two log-normal quantities, `log-log Pearson` (power-law fit) is more appropriate.
- With n_raw = 670 per-detection samples, even r ≈ 0.12 crosses conventional p < 0.01. Native binning to n = 40 gives honest effect sizes and honest p-values — which is why we switched.

### Commit message
`v1.06 Feature: E27 spectral correlation notebook (hamogram vs B_N, three-target pipeline)`
