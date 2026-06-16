"""
FFT spectrogram for magnetic hole analysis.

Uses scipy.signal.spectrogram (STFT) — fast, single-call, no custom code.
CWT wavelet transform available as optional upgrade if finer multi-resolution
analysis is needed later.
"""

import numpy as np
import scipy.signal
import time as _time


def compute_spectrogram(signal, fs, nperseg=1024, noverlap=None, freq_range=None):
    """
    Compute a spectrogram via STFT.

    Args:
        signal: 1D array of real values
        fs: sampling frequency in Hz
        nperseg: FFT window size (controls freq resolution vs time resolution)
        noverlap: overlap between windows (default: nperseg // 2)
        freq_range: (f_low, f_high) in Hz to clip output

    Returns:
        freqs, times_sec, power (all numpy arrays)
    """
    if noverlap is None:
        noverlap = nperseg // 2

    clean = np.asarray(signal, dtype=np.float64)
    nans = np.isnan(clean)
    if nans.any():
        good = np.where(~nans)[0]
        clean[nans] = np.interp(np.where(nans)[0], good, clean[good])

    t0 = _time.perf_counter()
    freqs, times_sec, Sxx = scipy.signal.spectrogram(
        clean, fs=fs, nperseg=nperseg, noverlap=noverlap,
        window='hann', scaling='density'
    )
    elapsed = _time.perf_counter() - t0

    if freq_range is not None:
        mask = (freqs >= freq_range[0]) & (freqs <= freq_range[1])
        freqs = freqs[mask]
        Sxx = Sxx[mask]

    print(f"  ⏱️  Spectrogram: {elapsed:.3f}s ({len(signal):,} samples, "
          f"nperseg={nperseg}, {Sxx.shape[0]} freq bins × {Sxx.shape[1]} time bins)")

    return freqs, times_sec, Sxx


def render_spectrogram(freqs, times_sec, power, t_start=None, ax=None,
                       title="FFT Spectrogram", cmap='magma',
                       save_path=None, dpi=150):
    """
    Render a spectrogram image.

    Args:
        freqs: frequency array from compute_spectrogram
        times_sec: time array in seconds from compute_spectrogram
        power: 2D power array [n_freqs, n_times]
        t_start: datetime for the start of the signal (makes x-axis absolute)
        ax: optional matplotlib Axes
        title: plot title
        cmap: colormap
        save_path: if provided, save figure
        dpi: resolution
    """
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates

    if ax is None:
        fig, ax = plt.subplots(figsize=(16, 6))
    else:
        fig = ax.get_figure()

    log_power = 10 * np.log10(power + 1e-20)
    median = np.median(log_power)
    std = np.std(log_power)
    vmin = median - 2.5 * std
    vmax = median + 6 * std

    if t_start is not None:
        import pandas as pd
        t_abs = pd.Timestamp(t_start) + pd.to_timedelta(times_sec, unit='s')
        x_vals = t_abs.to_pydatetime()
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
        ax.set_xlabel('Time (UTC)')
    else:
        x_vals = times_sec
        ax.set_xlabel('Time (s)')

    mesh = ax.pcolormesh(x_vals, freqs, log_power,
                         cmap=cmap, shading='auto', vmin=vmin, vmax=vmax)
    ax.set_xlim(x_vals[0], x_vals[-1])
    ax.set_yscale('log')
    ax.set_ylabel('Frequency (Hz)')
    ax.set_title(title)
    fig.colorbar(mesh, ax=ax, label='Power (dB)')

    if save_path:
        fig.tight_layout()
        fig.savefig(save_path, bbox_inches='tight', dpi=dpi)
        print(f"  Spectrogram saved to {save_path}")

    return fig, ax
