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

## Build single-file EXE

Jika ingin hasil akhir hanya satu file `.exe`, double-click:

```bat
build_onefile_exe.bat
```

Output:

```text
dist\HydroTidePro.exe
```

Catatan single-file:

- Lebih praktis dibagikan karena hanya satu file.
- Startup pertama biasanya lebih lambat karena PyInstaller mengekstrak file internal ke folder temporary.
- Sample data dan assets ikut dibundel di dalam `.exe`, tetapi tidak terlihat sebagai folder terpisah. Jika ingin sample data terlihat sebagai file biasa, gunakan build one-folder.
