import numpy as np
import pandas as pd


def _find_peaks(values):
    values = np.asarray(values, dtype=float)
    if len(values) < 3:
        return np.array([], dtype=int)

    prev_values = values[:-2]
    current_values = values[1:-1]
    next_values = values[2:]
    peak_mask = (current_values > prev_values) & (current_values >= next_values)
    return np.where(peak_mask)[0] + 1


def compute_important_levels(time_array, height_array):
    """
    Menghitung 7 Important Levels beserta jumlah kejadiannya,
    berdasarkan deteksi puncak (pasang) dan lembah (surut)
    pada kurva pasut (observasi atau hasil prediksi 1 tahun).

    Returns:
        dict: { "HWS": (value, count), "MHWS": (value, count), ... }
    """
    heights = np.asarray(height_array)
    times = pd.to_datetime(pd.Series(time_array)).reset_index(drop=True)

    n_total = len(heights)
    msl = heights.mean()

    high_idx = _find_peaks(heights)
    low_idx = _find_peaks(-heights)

    if len(high_idx) == 0 or len(low_idx) == 0:
        raise ValueError("Tidak cukup variasi data untuk mendeteksi puncak pasang/surut.")

    highs = heights[high_idx]
    lows = heights[low_idx]
    high_times = times.iloc[high_idx].reset_index(drop=True)
    low_times = times.iloc[low_idx].reset_index(drop=True)

    cycle_hours = 14.77 * 24
    start_time = times.iloc[0]

    high_cycle = ((high_times - start_time) / pd.Timedelta(hours=cycle_hours)).astype(int)
    low_cycle = ((low_times - start_time) / pd.Timedelta(hours=cycle_hours)).astype(int)

    df_high = pd.DataFrame({'val': highs, 'cycle': high_cycle})
    df_low = pd.DataFrame({'val': lows, 'cycle': low_cycle})

    spring_highs = df_high.groupby('cycle')['val'].max()
    spring_lows = df_low.groupby('cycle')['val'].min()

    hws = highs.max()
    lws = lows.min()
    mhws = spring_highs.mean()
    mlws = spring_lows.mean()
    mhwl = highs.mean()
    mlwl = lows.mean()

    levels = {
        "HWS":  (hws, 1),
        "MHWS": (mhws, len(spring_highs)),
        "MHWL": (mhwl, len(highs)),
        "MSL":  (msl, n_total),
        "MLWL": (mlwl, len(lows)),
        "MLWS": (mlws, len(spring_lows)),
        "LWS":  (lws, 1),
    }
    return levels


def format_levels_text(levels):
    """
    Mencetak levels dalam format teks sesuai standar Admiralty:
    Highest Water Spring   (HWS ) :    2.62, Jml. Kejadian :      1
    """
    labels = {
        "HWS":  "Highest Water Spring",
        "MHWS": "Mean High Water Spring",
        "MHWL": "Mean High Water Level",
        "MSL":  "Mean Sea Level",
        "MLWL": "Mean Low Water Level",
        "MLWS": "Mean Low Water Spring",
        "LWS":  "Lowest Water Spring",
    }
    order = ["HWS", "MHWS", "MHWL", "MSL", "MLWL", "MLWS", "LWS"]

    lines = []
    for key in order:
        value, count = levels[key]
        label = f"{labels[key]:<22}"
        code = f"({key:<4})"
        lines.append(f"{label} {code} : {value:8.2f}, Jml. Kejadian : {count:6d}")
    return "\n".join(lines)
