from engine.importer import load_and_standardize_data
from engine.least_square import LeastSquareEngine
from engine.lstsq_engine import LSTSQEngine
from engine.admiralty import AdmiraltyEngine


def perform_analysis(file_path, method='ols'):
    df = load_and_standardize_data(file_path)

    if df is None or df.empty:
        raise ValueError("Data gagal dimuat atau kosong setelah pembersihan.")

    if method == 'ols':
        return LeastSquareEngine().run_analysis(df)
    elif method == 'lstsq':
        return LSTSQEngine().run_analysis(df)
    elif method == 'admiralty':
        return AdmiraltyEngine().run_analysis(df)
    else:
        raise ValueError(f"Metode '{method}' tidak dikenal. Gunakan: 'ols', 'lstsq', atau 'admiralty'")
