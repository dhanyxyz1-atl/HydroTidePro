import os
from pathlib import Path

import numpy as np
import pandas as pd

from engine.importer import load_and_standardize_data
from engine.processor import perform_analysis


METHODS = [
    ("admiralty", "Admiralty Method"),
    ("lstsq", "Least Square (NumPy)"),
]

SAMPLE_CASES = [
    Path("sample_data/sample_29_days.csv"),
    Path("sample_data/sample_29_days.xlsx"),
    Path("sample_data/sample_31_days.csv"),
    Path("sample_data/sample_31_days.xlsx"),
]

QUALITY_THRESHOLDS = {
    "admiralty": {"min_r2": 0.85, "max_rmse": 0.08},
    "lstsq": {"min_r2": 0.95, "max_rmse": 0.05},
}


def generate_dummy_data(path="dummy_test.csv", days=30):
    rng = np.random.default_rng(20260707)
    periods = days * 24
    time_range = pd.date_range(start="2026-07-01", periods=periods, freq="h")
    t_hours = np.arange(periods)
    height = (
        2.0
        + 0.6 * np.cos(2 * np.pi * t_hours / 12.42)
        + 0.2 * np.cos(2 * np.pi * t_hours / 12.0)
        + 0.3 * np.cos(2 * np.pi * t_hours / 23.93)
        + 0.2 * np.cos(2 * np.pi * t_hours / 25.82)
        + rng.normal(0, 0.02, periods)
    )
    df = pd.DataFrame({"time": time_range, "height": height})
    df.to_csv(path, index=False, header=False, date_format="%d-%m-%Y %H:%M")
    return path


def check_result_contract(result, label):
    print(f"      Checking output contract ({label})...")
    required_keys = ["constituents", "formzahl", "type", "levels", "rmse", "reconstructor"]
    all_ok = True
    for key in required_keys:
        if key in result:
            print(f"        OK: key '{key}' found.")
        else:
            print(f"        ERROR: key '{key}' is missing.")
            all_ok = False

    df_const = result.get("constituents")
    if df_const is not None and "Speed" not in df_const.columns:
        print("        ERROR: 'Speed' column is missing in constituents.")
        all_ok = False
    else:
        print("        OK: 'Speed' column found in constituents.")
    return all_ok


def check_reconstruct(result, label):
    print(f"      Testing reconstruct() ({label})...")
    try:
        reconstructor = result["reconstructor"]
        start_time = result.get("start_time", pd.Timestamp("2026-01-01"))
        time_range = pd.date_range(start=start_time, periods=48, freq="h")
        predicted = reconstructor.reconstruct(time_range, result["constituents"])

        if np.any(np.isnan(predicted)):
            print("        ERROR: reconstruct result contains NaN.")
            return False
        if np.allclose(predicted, predicted[0]):
            print("        ERROR: reconstruct result is constant.")
            return False
        if np.max(np.abs(predicted)) > 100:
            print(
                "        ERROR: unrealistic value (>100 m): "
                f"{predicted.min():.2f} to {predicted.max():.2f}."
            )
            return False

        print(
            f"        OK: reconstruct() produced {len(predicted)} points, "
            f"range {predicted.min():.3f} to {predicted.max():.3f} m."
        )
        return True
    except Exception as exc:
        print(f"        ERROR during reconstruct: {exc}")
        return False


def check_quality(result, method):
    threshold = QUALITY_THRESHOLDS.get(method)
    if not threshold:
        return True

    r2 = result.get("r2")
    rmse = result.get("rmse")
    if r2 is None:
        print("      ERROR: R2 is missing.")
        return False
    if rmse is None:
        print("      ERROR: RMSE is missing.")
        return False

    r2_ok = r2 >= threshold["min_r2"]
    rmse_ok = rmse <= threshold["max_rmse"]
    print(
        "      Quality threshold: "
        f"R2 >= {threshold['min_r2']:.2f}, RMSE <= {threshold['max_rmse']:.3f} m"
    )
    print(f"        R2   : {r2:.4f} ({'OK' if r2_ok else 'FAIL'})")
    print(f"        RMSE : {rmse:.4f} m ({'OK' if rmse_ok else 'FAIL'})")
    return r2_ok and rmse_ok


def describe_input(filepath):
    df = load_and_standardize_data(filepath)
    if df is None or df.empty:
        return "input failed to load"

    start = df["time"].min()
    end = df["time"].max()
    duration_days = ((end - start).total_seconds() / 3600.0 + 1.0) / 24.0
    return (
        f"{len(df)} rows, {duration_days:.2f} days, "
        f"{start:%Y-%m-%d %H:%M} to {end:%Y-%m-%d %H:%M}"
    )


def run_method_test(filepath, method, label, enforce_quality=False):
    print(f"\n[TEST] {filepath} | method='{method}' ({label})")
    try:
        print(f"      Input: {describe_input(filepath)}")
        result = perform_analysis(filepath, method=method)
        print("      Gateway call succeeded.")

        contract_ok = check_result_contract(result, label)
        reconstruct_ok = check_reconstruct(result, label)
        quality_ok = check_quality(result, method) if enforce_quality else True

        print(f"      Tide Type  : {result['type']}")
        print(f"      Formzahl   : {result['formzahl']:.4f}")
        print(f"      RMSE       : {result.get('rmse', float('nan')):.4f} m")
        r2 = result.get("r2")
        if r2 is not None:
            print(f"      R2         : {r2:.4f}")
        if result.get("quality"):
            print(f"      Quality    : {result['quality']}")
        print(f"      Levels     : {list(result['levels'].keys())}")

        status = "PASS" if (contract_ok and reconstruct_ok and quality_ok) else "PARTIAL/FAIL"
        print(f"      >> Status: {status}")
        return contract_ok and reconstruct_ok and quality_ok

    except Exception as exc:
        print(f"      CRITICAL ERROR: {exc}")
        return False


def run_dummy_smoke_tests():
    print("\n=== Smoke Test: Synthetic Dummy Data ===")
    filepath = generate_dummy_data()
    print(f"[Setup] Dummy data created: {filepath} ({os.path.getsize(filepath)} bytes)")

    results = []
    for method, label in METHODS:
        results.append(run_method_test(filepath, method, label, enforce_quality=False))
    return results


def run_sample_regression_tests():
    print("\n=== Regression Test: HydroTidePro Sample Import Data ===")
    results = []
    missing = [path for path in SAMPLE_CASES if not path.exists()]
    if missing:
        print("Missing sample files:")
        for path in missing:
            print(f"  - {path}")
        return [False]

    for sample_path in SAMPLE_CASES:
        for method, label in METHODS:
            results.append(
                run_method_test(
                    str(sample_path),
                    method,
                    label,
                    enforce_quality=True,
                )
            )
    return results


def verify_system():
    print("--- HydroTide Pro System Crosscheck ---")
    print("Smoke tests verify the app contract. Sample tests verify realistic import data.")

    results = []
    results.extend(run_dummy_smoke_tests())
    results.extend(run_sample_regression_tests())

    print("\n--- Summary ---")
    print("ALL TESTS PASSED." if all(results) else "SOME TESTS FAILED - check the log above.")
    print("--- Crosscheck Finished ---")


if __name__ == "__main__":
    verify_system()
