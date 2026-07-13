from engine.importer import load_and_standardize_data
from engine.lstsq_engine import LSTSQEngine
from engine.admiralty import AdmiraltyEngine
from app_info import APP_VERSION, DEVELOPER_NAME
import os


METHOD_LABELS = {
    "lstsq": "Least Square (NumPy)",
    "admiralty": "Admiralty Method",
}


def perform_analysis(file_path, method='lstsq'):
    df = load_and_standardize_data(file_path)

    if df is None or df.empty:
        raise ValueError("Data failed to load or is empty after cleaning.")

    result = perform_analysis_from_df(
        df,
        method=method,
        source_file=os.path.basename(file_path),
        source_path=os.path.abspath(file_path),
    )
    return result


def perform_analysis_from_df(df, method='lstsq', source_file="DataFrame", source_path=None):
    if df is None or df.empty:
        raise ValueError("Data failed to load or is empty after cleaning.")

    if method == 'lstsq':
        result = LSTSQEngine().run_analysis(df)
    elif method == 'admiralty':
        result = AdmiraltyEngine().run_analysis(df)
    else:
        raise ValueError(f"Unknown method: '{method}'. Choose 'lstsq' or 'admiralty'.")

    result["observed_prediction"] = _build_observed_prediction(df, result)
    result.update(_build_metadata(source_file, df, method, source_path=source_path))
    return result


def _build_observed_prediction(df, result):
    observed = df[["time", "height"]].copy()
    observed = observed.rename(columns={"height": "observed_height"})
    try:
        predicted = result["reconstructor"].reconstruct(
            observed["time"],
            result.get("constituents"),
        )
        observed["predicted_height"] = predicted
        observed["residual"] = observed["observed_height"] - observed["predicted_height"]
    except Exception:
        observed["predicted_height"] = None
        observed["residual"] = None
    return observed


def _build_metadata(source_file, df, method, source_path=None):
    time_start = df["time"].min()
    time_end = df["time"].max()
    duration_hours = (time_end - time_start).total_seconds() / 3600.0 if len(df) > 1 else 0.0
    data_days = (duration_hours / 24.0) + (1.0 / 24.0)

    return {
        "method": method,
        "method_label": METHOD_LABELS.get(method, method),
        "source_file": os.path.basename(str(source_file)),
        "source_path": os.path.abspath(source_path) if source_path else "-",
        "data_points": int(len(df)),
        "data_days": float(data_days),
        "data_start": time_start,
        "data_end": time_end,
        "developer": DEVELOPER_NAME,
        "app_version": APP_VERSION,
    }
