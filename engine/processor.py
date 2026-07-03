from engine.importer import load_and_standardize_data
from engine.lstsq_engine import LSTSQEngine
from engine.admiralty import AdmiraltyEngine


def perform_analysis(file_path, method='lstsq'):
    df = load_and_standardize_data(file_path)

    if df is None or df.empty:
        raise ValueError("Data gagal dimuat atau kosong setelah pembersihan.")

    if method == 'lstsq':
        return LSTSQEngine().run_analysis(df)
    elif method == 'admiralty':
        return AdmiraltyEngine().run_analysis(df)
    else:
        raise ValueError(f"Metode tidak dikenal: '{method}'. Pilih 'lstsq' atau 'admiralty'.")