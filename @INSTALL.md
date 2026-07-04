# Launching HydroTide Pro menjadi EXE

## Build di Windows

1. Install Python 3.11 atau 3.12.
2. Extract folder proyek HydroTidePro.
3. Double-click:

```bat
build_exe.bat
```

Hasil build:

```text
dist\HydroTidePro\HydroTidePro.exe
```

## File yang dikirim ke user

Kirim seluruh folder:

```text
dist\HydroTidePro
```

Jangan hanya kirim file `.exe`, karena mode build ini memakai folder release agar PyQt6, matplotlib, dan sample data lebih stabil.

## Sample data

Folder release menyertakan:

```text
sample_data\sample_29_days.csv
sample_data\sample_31_days.csv
sample_data\sample_29_days.xlsx
sample_data\sample_31_days.xlsx
```

CSV dan XLSX bisa diimport langsung dari aplikasi.

## Catatan

- Build ini memakai PyInstaller one-folder.
- Jika Windows Defender memberi peringatan pada build pertama, pilih allow/trust untuk folder build pribadi Anda.
- Untuk distribusi formal, zip folder `dist\HydroTidePro`.
