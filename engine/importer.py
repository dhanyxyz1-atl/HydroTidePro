import pandas as pd
import os

def load_and_standardize_data(filepath):
    """
    Fungsi cerdas untuk import data pasut.
    Perbaikan:
      - Bisa membaca file dengan/ tanpa header
      - Jika ada >2 kolom, ambil dua kolom pertama (waktu, tinggi)
      - Penanganan format tanggal lebih robust
    """
    try:
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"File tidak ditemukan: {filepath}")

        ext = os.path.splitext(filepath)[1].lower()

        if ext in [".xlsx", ".xls"]:
            df = pd.read_excel(filepath)
            if df.shape[1] < 2:
                df = pd.read_excel(filepath, header=None)
        else:
            # Baca baris pertama untuk deteksi header sederhana
            with open(filepath, 'r', encoding='utf-8-sig') as f:
                first_line = f.readline().strip()

            # Jika ada huruf pada baris pertama besar kemungkinan header
            has_header = any(char.isalpha() for char in first_line)

            if has_header:
                df = pd.read_csv(filepath, sep=None, engine='python', encoding='utf-8-sig')
            else:
                df = pd.read_csv(filepath, sep=None, engine='python', header=None,
                                  encoding='utf-8-sig')

        if ext in [".xlsx", ".xls"] and len(df) and _looks_like_data_row(df.columns):
            df = pd.read_excel(filepath, header=None)

        # Jika banyak kolom, ambil dua kolom pertama
        if df.shape[1] > 2:
            df = df.iloc[:, :2]

        # Pastikan nama kolom konsisten
        df.columns = ['time', 'height']

        # Bersihkan kolom time text
        raw_time = (
            df['time'].astype(str)
            .str.strip()
            .str.replace('/', '-', regex=False)
        )

        candidate_formats = [
            '%d-%m-%Y %H:%M',
            '%d-%m-%Y %H:%M:%S',
            '%Y-%m-%d %H:%M',
            '%Y-%m-%d %H:%M:%S',
            '%m-%d-%Y %H:%M',
            '%d-%m-%y %H:%M',
        ]

        parsed = pd.Series(pd.NaT, index=raw_time.index)
        remaining_mask = parsed.isna()

        for fmt in candidate_formats:
            if not remaining_mask.any():
                break
            attempt = pd.to_datetime(
                raw_time[remaining_mask], format=fmt, errors='coerce'
            )
            parsed.loc[remaining_mask] = attempt
            remaining_mask = parsed.isna()

        # last resort: dayfirst parse fleksibel
        if remaining_mask.any():
            attempt = pd.to_datetime(raw_time[remaining_mask], dayfirst=True, errors='coerce')
            parsed.loc[remaining_mask] = attempt
            remaining_mask = parsed.isna()

        df['time'] = parsed
        df['height'] = pd.to_numeric(df['height'], errors='coerce')

        n_before = len(df)
        if remaining_mask.any():
            print("Contoh nilai yang tetap gagal parse (time):")
            print(raw_time[remaining_mask].head(20).tolist())

        df = df.dropna(subset=['time', 'height']).reset_index(drop=True)
        n_after = len(df)
        if n_before != n_after:
            print(f"Peringatan: {n_before - n_after} baris dibuang karena format tanggal/tinggi tidak terbaca.")

        return df
    except Exception as e:
        print(f"Error di importer: {e}")
        return None


def _looks_like_data_row(columns):
    joined = " ".join(str(col).lower() for col in columns)
    return any(char.isdigit() for char in joined) and "time" not in joined
