import os
from datetime import date, datetime

import pandas as pd

from engine.importer import load_and_standardize_data


def load_tide_series(filepath, preferred="auto"):
    ext = os.path.splitext(filepath)[1].lower()
    if ext in {".xlsx", ".xls", ".xlsm"}:
        template = _load_invert_shift_template(filepath, preferred=preferred)
        if template is not None and not template.empty:
            return template

    df = load_and_standardize_data(filepath)
    if df is None or df.empty:
        raise ValueError(f"No readable tide data found in {os.path.basename(filepath)}.")
    return _clean_tide_frame(df)


def load_reference_series(filepath):
    ext = os.path.splitext(filepath)[1].lower()
    if ext in {".xlsx", ".xls", ".xlsm"}:
        template = _load_invert_shift_template(filepath, preferred="reference")
        if template is not None and not template.empty:
            return template
    return load_tide_series(filepath)


def load_embedded_reference_series(filepath):
    ext = os.path.splitext(filepath)[1].lower()
    if ext not in {".xlsx", ".xls", ".xlsm"}:
        return None
    return _load_invert_shift_template(filepath, preferred="reference")


def invert_and_shift_tide(source_df, reference_df=None):
    source = _clean_tide_frame(source_df)
    if source.empty:
        raise ValueError("Source tide data is empty.")

    source_hwl = float(source["height"].max())
    source_lwl = float(source["height"].min())
    source_msl = (source_hwl + source_lwl) / 2.0

    output = pd.DataFrame({
        "time": source["time"],
        "raw_height": source["height"],
    })
    output["inverted_height"] = source_msl - output["raw_height"]

    reference_stats = None
    if reference_df is not None and not reference_df.empty:
        reference = _clean_tide_frame(reference_df)
        reference_hwl = float(reference["height"].max())
        reference_lwl = float(reference["height"].min())
        reference_msl = (reference_hwl + reference_lwl) / 2.0
        output["shifted_height"] = reference_msl + output["inverted_height"]
        reference_stats = {
            "hwl": reference_hwl,
            "lwl": reference_lwl,
            "msl": reference_msl,
            "points": int(len(reference)),
        }
    else:
        output["shifted_height"] = output["inverted_height"]

    analysis_df = output[["time", "shifted_height"]].rename(
        columns={"shifted_height": "height"}
    )

    return {
        "source": source,
        "reference": reference_df,
        "processed": output,
        "analysis": analysis_df,
        "source_stats": {
            "hwl": source_hwl,
            "lwl": source_lwl,
            "msl": source_msl,
            "points": int(len(source)),
        },
        "reference_stats": reference_stats,
        "note": _build_note(reference_stats),
    }


def _build_note(reference_stats):
    if reference_stats:
        return (
            "Invert uses source MSL minus raw height; shift uses reference MSL "
            "plus inverted height, matching the Excel template logic."
        )
    return (
        "Invert uses source MSL minus raw height. No reference file was supplied, "
        "so the shifted output is equal to the inverted tide."
    )


def _load_invert_shift_template(filepath, preferred="auto"):
    try:
        df = pd.read_excel(filepath, sheet_name=0, header=None, engine="openpyxl")
    except Exception:
        return None

    pairs = _detect_template_pairs(df)
    if preferred == "reference" and "reference" in pairs:
        return pairs["reference"]
    if preferred == "source" and "source" in pairs:
        return pairs["source"]
    if preferred == "processed" and "processed" in pairs:
        return pairs["processed"]
    if "source" in pairs:
        return pairs["source"]
    if "reference" in pairs:
        return pairs["reference"]
    return None


def _detect_template_pairs(df):
    pairs = {}
    rows, cols = df.shape

    for col in range(cols - 1):
        header = str(df.iat[0, col]).strip().lower() if rows else ""
        label = header

        if "raw radar" in label:
            key = "source"
        elif "shifted" in label:
            key = "processed"
        elif "shifting" in label:
            key = "shift_stats"
        elif "valeport" in label:
            key = "reference"
        elif "inverted" in label:
            key = "inverted"
        else:
            continue

        if key == "shift_stats":
            continue

        candidate = pd.DataFrame({
            "time": df.iloc[1:, col],
            "height": df.iloc[1:, col + 1],
        })
        candidate = _clean_tide_frame(candidate)
        if not candidate.empty:
            if key not in pairs or len(candidate) > len(pairs[key]):
                pairs[key] = candidate

    return pairs


def _clean_tide_frame(df):
    cleaned = df.copy()
    cleaned = cleaned.iloc[:, :2]
    cleaned.columns = ["time", "height"]
    time_values = cleaned["time"]
    has_datetime_values = time_values.map(lambda value: isinstance(value, (datetime, date, pd.Timestamp))).any()
    if has_datetime_values:
        cleaned["time"] = pd.to_datetime(time_values, errors="coerce")
    else:
        cleaned["time"] = pd.to_datetime(time_values, errors="coerce", dayfirst=True)
    cleaned["height"] = pd.to_numeric(cleaned["height"], errors="coerce")
    cleaned = cleaned.dropna(subset=["time", "height"])
    cleaned = cleaned.sort_values("time").drop_duplicates(subset="time")
    return cleaned.reset_index(drop=True)
