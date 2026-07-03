import pandas as pd
import os
from engine.levels import format_levels_text


def export_results(result, filepath, predicted_df=None):
    """
    Mengekspor hasil analisis pasut ke file Excel (.xlsx) atau CSV (.csv).

    Args:
        result (dict): Output dari run_analysis (berisi 'constituents', 'levels', dst).
            'levels' berformat {"HWS": (value, count), ...}
        filepath (str): Path tujuan file, ekstensi menentukan format (.xlsx atau .csv).
        predicted_df (pd.DataFrame, optional): DataFrame prediksi (kolom 'time', 'height').
    """
    ext = os.path.splitext(filepath)[1].lower()

    df_const = result['constituents'].copy()

    levels = result['levels']
    df_levels = pd.DataFrame([
        {"Level": key, "Value (m)": value, "Jml. Kejadian": count}
        for key, (value, count) in levels.items()
    ])

    df_summary = pd.DataFrame([{
        "Formzahl": result.get('formzahl'),
        "Tipe Pasut": result.get('type'),
        "RMSE": result.get('rmse'),
    }])

    levels_text = format_levels_text(levels)

    if ext == '.xlsx':
        with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
            df_summary.to_excel(writer, sheet_name='Summary', index=False)
            df_const.to_excel(writer, sheet_name='Constituents', index=False)
            df_levels.to_excel(writer, sheet_name='Important Levels', index=False)

            # Sheet tambahan: format teks asli (HWS, MHWS, dst) seperti laporan Admiralty
            df_levels_text = pd.DataFrame({"Important Levels Report": levels_text.split("\n")})
            df_levels_text.to_excel(writer, sheet_name='Levels Report', index=False)

            if predicted_df is not None:
                predicted_df.to_excel(writer, sheet_name='Prediction', index=False)

    elif ext == '.csv':
        base, _ = os.path.splitext(filepath)
        df_summary.to_csv(f"{base}_summary.csv", index=False)
        df_const.to_csv(f"{base}_constituents.csv", index=False)
        df_levels.to_csv(f"{base}_levels.csv", index=False)

        with open(f"{base}_levels_report.txt", "w", encoding="utf-8") as f:
            f.write(levels_text)

        if predicted_df is not None:
            predicted_df.to_csv(f"{base}_prediction.csv", index=False)
    else:
        raise ValueError("Format file tidak didukung. Gunakan .xlsx atau .csv")