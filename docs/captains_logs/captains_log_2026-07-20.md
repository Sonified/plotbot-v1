# Captain's Log -- 2026-07-20

## v1.16 -- LF spectrograms, spectrogram title fixes, new E28 audification

### Ultra-low-frequency spectrograms

Added `composite_LF/` folders to all 5 Holey Grail regions with spectrograms using mag_rtn_4sa (4 Sa/s) instead of full-cadence mag_rtn (293 Hz). This resolves frequencies down to ~0.0001 Hz (periods up to ~2.3 hours) with the upper bound capped at 0.5 Hz so LF features aren't squished. All rendered as composite (with |B| trace overlay) at 3 resolutions (nperseg 8192, 16384, 32768).

### Spectrogram title fixes

All spectrogram titles in `batch_scan.py` now include `|B|` to identify the component. Previously titles just showed the region label and nperseg. Also renamed the composite suffix from `+ |B|` to `+ trace` since the spectrogram itself is |B| and the overlay is the time series trace.

### New E28 audification trange for Jaye

Added `2026/06/15 12:00 - 2026/06/16 12:00` to the audification notebook. Previous E28 renders (CME Leg June 5, HCS crossing June 8-9) commented out but preserved in the trange history.
