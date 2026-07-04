import os
import numpy as np
import pandas as pd
from engine.processor import perform_analysis


def generate_dummy_data(path="dummy_test.csv", days=30):
    periods = days * 24
    time_range = pd.date_range(start="2026-07-01", periods=periods, freq="h")
    t_hours = np.arange(periods)
    height = (
        2.0
        + 0.6 * np.cos(2 * np.pi * t_hours / 12.42)
        + 0.2 * np.cos(2 * np.pi * t_hours / 12.0)
        + 0.3 * np.cos(2 * np.pi * t_hours / 23.93)
        + 0.2 * np.cos(2 * np.pi * t_hours / 25.82)
        + np.random.normal(0, 0.02, periods)
    )
    df = pd.DataFrame({"time": time_range, "height": height})
    df.to_csv(path, index=False, header=False, date_format="%d-%m-%Y %H:%M")
    return path


def check_result_contract(result, label):
    print(f"      Memverifikasi Kontrak Output ({label})...")
    required_keys = ["constituents", "formzahl", "type", "levels", "rmse", "reconstructor"]
    all_ok = True
    for key in required_keys:
        if key in result:
            print(f"        OK: Key '{key}' ditemukan.")
        else:
            print(f"        ERROR: Key '{key}' hilang!")
            all_ok = False

    df_const = result.get("constituents")
    if df_const is not None and "Speed" not in df_const.columns:
        print("        ERROR: Kolom 'Speed' hilang di constituents!")
        all_ok = False
    else:
        print("        OK: Kolom 'Speed' ada di constituents.")
    return all_ok


def check_reconstruct(result, label):
    print(f"      Menguji reconstruct() ({label})...")
    try:
        reconstructor = result["reconstructor"]
        time_range = pd.date_range(start=pd.Timestamp.now(), periods=48, freq="h")
        predicted = reconstructor.reconstruct(time_range, result["constituents"])

        if np.any(np.isnan(predicted)):
            print("        ERROR: Hasil reconstruct mengandung NaN!")
            return False
        if np.all(predicted == predicted[0]):
            print("        ERROR: Hasil reconstruct konstan (tidak ada variasi pasut)!")
            return False
        if np.max(np.abs(predicted)) > 100:
            print(f"        ERROR: Nilai tidak wajar (>100 m): "
                  f"{predicted.min():.2f} s/d {predicted.max():.2f}!")
            return False

        print(f"        OK: reconstruct() menghasilkan {len(predicted)} titik, "
              f"range {predicted.min():.3f} s/d {predicted.max():.3f} m.")
        return True
    except Exception as e:
        print(f"        ERROR saat reconstruct: {e}")
        return False


def run_method_test(filepath, method, label):
    print(f"\n[Uji] Method = '{method}' ({label})")
    try:
        result = perform_analysis(filepath, method=method)
        print("      Gateway berhasil dipanggil.")

        contract_ok = check_result_contract(result, label)
        reconstruct_ok = check_reconstruct(result, label)

        print(f"      Tipe Pasut Terdeteksi : {result['type']}")
        print(f"      Formzahl              : {result['formzahl']:.4f}")
        rmse = result.get('rmse')
        print(f"      RMSE                  : {rmse:.4f}" if rmse is not None
              else "      RMSE                  : (tidak tersedia)")
        print(f"      Levels                : {list(result['levels'].keys())}")

        status = "LULUS" if (contract_ok and reconstruct_ok) else "GAGAL SEBAGIAN"
        print(f"      >> Status: {status}")
        return contract_ok and reconstruct_ok

    except Exception as e:
        print(f"      CRITICAL ERROR: {e}")
        return False


def verify_system():
    print("--- Memulai Crosscheck Sistem HydroTidePro ---")
    filepath = generate_dummy_data()
    print(f"[Setup] Data dummy dibuat: {filepath} ({os.path.getsize(filepath)} bytes)")

    results = []
    results.append(run_method_test(filepath, "admiralty", "Admiralty Method"))
    results.append(run_method_test(filepath, "lstsq", "Least Square (NumPy)"))

    print("\n--- Ringkasan ---")
    print("SEMUA TES LULUS." if all(results) else "ADA TES YANG GAGAL — periksa log di atas.")
    print("--- Crosscheck Selesai ---")


if __name__ == "__main__":
    verify_system()