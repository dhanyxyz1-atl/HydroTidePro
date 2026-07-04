from engine.importer import load_and_standardize_data
from engine.lstsq_engine import LSTSQEngine
from engine.admiralty import AdmiraltyEngine
import os


DEVELOPER_NAME = "dhanyxyz1-atl"


METHOD_LABELS = {
    "lstsq": "Least Square (NumPy)",
    "admiralty": "Admiralty Method",
}


def perform_analysis(file_path, method='lstsq'):
    df = load_and_standardize_data(file_path)

    if df is None or df.empty:
        raise ValueError("Data gagal dimuat atau kosong setelah pembersihan.")

    if method == 'lstsq':
        result = LSTSQEngine().run_analysis(df)
    elif method == 'admiralty':
        result = AdmiraltyEngine().run_analysis(df)
    else:
        raise ValueError(f"Metode tidak dikenal: '{method}'. Pilih 'lstsq' atau 'admiralty'.")

    result.update(_build_metadata(file_path, df, method))
    return result


def _build_metadata(file_path, df, method):
    time_start = df["time"].min()
    time_end = df["time"].max()
    duration_hours = (time_end - time_start).total_seconds() / 3600.0 if len(df) > 1 else 0.0
    data_days = (duration_hours / 24.0) + (1.0 / 24.0)

    return {
        "method": method,
        "method_label": METHOD_LABELS.get(method, method),
        "source_file": os.path.basename(file_path),
        "source_path": os.path.abspath(file_path),
        "data_points": int(len(df)),
        "data_days": float(data_days),
        "data_start": time_start,
        "data_end": time_end,
        "developer": DEVELOPER_NAME,
    }
