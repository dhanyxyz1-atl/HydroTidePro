import pandas as pd
import os
from engine.levels import format_levels_text


def _metadata_rows(result):
    return [
        ("Method", result.get("method_label", result.get("method", "-"))),
        ("Tide Type", result.get("type", "-")),
        ("Formzahl", result.get("formzahl")),
        ("RMSE (m)", result.get("rmse")),
        ("Source File", result.get("source_file", "-")),
        ("Source Path", result.get("source_path", "-")),
        ("Data Points", result.get("data_points", "-")),
        ("Data Duration (days)", result.get("data_days", "-")),
        ("Data Start", result.get("data_start", "-")),
        ("Data End", result.get("data_end", "-")),
        ("Developer", result.get("developer", "dhanyxyz1-atl")),
        ("Analysis Note", result.get("analysis_note", "-")),
    ]


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
        "Method": result.get("method_label", result.get("method", "-")),
        "Source File": result.get("source_file", "-"),
        "Data Duration (days)": result.get("data_days", "-"),
        "Developer": result.get("developer", "dhanyxyz1-atl"),
        "Formzahl": result.get('formzahl'),
        "Tipe Pasut": result.get('type'),
        "RMSE": result.get('rmse'),
    }])
    df_metadata = pd.DataFrame(_metadata_rows(result), columns=["Item", "Value"])

    levels_text = format_levels_text(levels)
    levels_report_lines = [
        f"Method                 : {result.get('method_label', result.get('method', '-'))}",
        f"Source File            : {result.get('source_file', '-')}",
        f"Data Duration          : {result.get('data_days', '-')} days",
        f"Developer              : {result.get('developer', 'dhanyxyz1-atl')}",
        "",
        *levels_text.split("\n"),
    ]

    if ext == '.xlsx':
        with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
            df_summary.to_excel(writer, sheet_name='Summary', index=False)
            df_metadata.to_excel(writer, sheet_name='Metadata', index=False)
            df_const.to_excel(writer, sheet_name='Constituents', index=False)
            df_levels.to_excel(writer, sheet_name='Important Levels', index=False)

            # Sheet tambahan: format teks asli (HWS, MHWS, dst) seperti laporan Admiralty
            df_levels_text = pd.DataFrame({"Important Levels Report": levels_report_lines})
            df_levels_text.to_excel(writer, sheet_name='Levels Report', index=False)

            if predicted_df is not None:
                predicted_df.to_excel(writer, sheet_name='Prediction', index=False)

            for sheet in writer.book.worksheets:
                sheet.freeze_panes = "A2"
                for cell in sheet[1]:
                    cell.font = cell.font.copy(bold=True)
                for column_cells in sheet.columns:
                    max_length = max(len(str(cell.value)) if cell.value is not None else 0 for cell in column_cells)
                    sheet.column_dimensions[column_cells[0].column_letter].width = min(max(max_length + 2, 12), 42)

    elif ext == '.csv':
        base, _ = os.path.splitext(filepath)
        df_summary.to_csv(f"{base}_summary.csv", index=False)
        df_metadata.to_csv(f"{base}_metadata.csv", index=False)
        df_const.to_csv(f"{base}_constituents.csv", index=False)
        df_levels.to_csv(f"{base}_levels.csv", index=False)

        with open(f"{base}_levels_report.txt", "w", encoding="utf-8") as f:
            f.write("\n".join(levels_report_lines))

        if predicted_df is not None:
            predicted_df.to_csv(f"{base}_prediction.csv", index=False)
    else:
        raise ValueError("Format file tidak didukung. Gunakan .xlsx atau .csv")
