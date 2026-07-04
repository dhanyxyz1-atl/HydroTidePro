# HydroTide Professional 🌊

Aplikasi analisis pasut harmonik dengan tiga metode: **Admiralty**, **Least Square (UTide)**, dan **Least Square (NumPy)** menggunakan `numpy.linalg.lstsq`.

## 📋 Daftar Isi
- [Fitur](#fitur)
- [Instalasi](#instalasi)
- [Penggunaan](#penggunaan)
- [Struktur Proyek](#struktur-proyek)
- [Metode Analisis](#metode-analisis)
- [Testing](#testing)

---

## ✨ Fitur

✅ **Tiga Metode Analisis:**
1. **Admiralty Method** - Menggunakan komponen harmonik tetap
2. **Least Square Combined 
		(UTide)** - Menggunakan library UTide (OLS fitting)
		(NumPy)** - Menggunakan `numpy.linalg.lstsq` (baru!)

✅ **Output:**
- Tabel konstituen harmonik (Amplitude, Phase, Speed)
- 7 Important Levels (HWS, MHWS, MHWL, MSL, MLWL, MLWS, LWS)
- Formzahl & Tipe Pasut (Semi-Diurnal, Mixed, Diurnal)
- RMSE (Root Mean Square Error)
- Prediksi 1 tahun dengan visualisasi grafik

✅ **Export:** Excel (.xlsx) atau CSV (.csv)

---

## 🚀 Instalasi

### 1. Clone Repository
```bash
git clone https://github.com/dhanyxyz1-atl/HydroTidePro.git
cd HydroTidePro
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### Build Windows EXE

Untuk membuat aplikasi menjadi `.exe` di Windows:

```bat
build_exe.bat
```

Output:

```text
dist\HydroTidePro\HydroTidePro.exe
```

Folder release juga menyertakan `sample_data` berisi contoh data 29 hari dan 31 hari dalam format CSV dan XLSX.

**requirements.txt:**
```
numpy>=1.21.0
pandas>=1.3.0
scipy>=1.7.0
PyQt6>=6.0.0
matplotlib>=3.4.0
openpyxl>=3.0.0
utide>=0.3.0  # Optional, untuk metode OLS
```

---

## 🎮 Penggunaan

### GUI (PyQt6)
```bash
python main.py
```

**Langkah:**
1. Pilih metode analisis:
   - **HARMONIC LEAST SQUARE'
   - **HARMONIC ADMIRALTY'
2. Klik **IMPORT DATA** → Pilih file CSV/TXT
3. Lihat hasil di tab **Constants** dan **Important Levels**
4. Klik **Predict 1 Year** untuk visualisasi
5. Klik **Export Results** untuk simpan ke Excel/CSV

### Command Line Testing
```bash
python run_check.py
```

Output akan menguji semua metode dengan data dummy 30 hari.

---

## 📁 Struktur Proyek

```
HydroTidePro/
├── engine/
│   ├── __init__.py
│   ├── importer.py           # Smart data loader
│   ├── levels.py             # Compute 7 Important Levels
│   ├── admiralty.py          # Admiralty Engine
│   ├── least_square.py       # UTide OLS Engine
│   ├── lstsq_engine.py       # NumPy lstsq Engine ⭐
│   └── processor.py          # Gateway (ols, lstsq, admiralty)
├── gui/
│   ├── __init__.py
│   ├── main_window.py        # 3 buttons GUI
│   └── result_window.py      # Result display & export
├── export/
│   ├── __init__.py
│   └── exporter.py           # Excel/CSV export
├── main.py                   # Entry point
├── run_check.py              # System verification
└── README.md                 # This file
```

---

## 🔬 Metode Analisis

### 1. Admiralty Method
- Komponen tetap: M2, S2, K1, O1
- Amplitude & phase dari konfigurasi hardcoded
- Cepat, tanpa fitting

### 2. Least Square (UTide/OLS)
- Library: `utide` (Codfish & Rich)
- 19 konstituen otomatis
- Fitting dengan OLS (Ordinary Least Squares)
- Confidence intervals

### 3. Least Square (NumPy) ⭐
**Implementasi:** `engine/lstsq_engine.py`

**Konsep:**
```
h(t) = Z0 + Σ(a_i·cos(ωi·t) + b_i·sin(ωi·t))
```

**Design Matrix:**
```
A = [1, cos(ω1·t), sin(ω1·t), cos(ω2·t), sin(ω2·t), ...]
x = [Z0, a1, b1, a2, b2, ...]
```

**Solve:**
```python
x, residuals, rank, s = np.linalg.lstsq(A, heights, rcond=None)
```

**Amplitude & Phase:**
```
Amplitude = √(a² + b²)
Phase = atan2(b, a)
```

**Kelebihan:**
- ✅ Murni NumPy (ringan, tanpa dependency eksternal)
- ✅ Kontrol penuh atas konstituen
- ✅ Transparan & mudah di-debug

**Kekurangan:**
- ❌ Tidak ada confidence intervals
- ❌ Konstituen dipilih manual

---

## 🧪 Testing

### Unit Test: `run_check.py`

```bash
python run_check.py
```

**Uji untuk setiap method:**
1. ✅ Kontrak output (semua keys ada?)
2. ✅ Kolom 'Speed' di constituents?
3. ✅ Reconstruct menghasilkan variasi pasut?
4. ✅ Range tinggi wajar (< 100 m)?
5. ✅ Formzahl & tipe pasut terdeteksi?

**Output contoh:**
```
--- Memulai Crosscheck Sistem HydroTidePro ---
[Setup] Data dummy dibuat: dummy_test.csv (2844 bytes)

[Uji] Method = 'admiralty' (Admiralty Method)
      Gateway berhasil dipanggil.
      Memverifikasi Kontrak Output (Admiralty Method)...
        OK: Key 'constituents' ditemukan.
        ...
      Tipe Pasut Terdeteksi : Admiralty Method
      Formzahl              : 0.8333
      RMSE                  : 0.0500
      >> Status: LULUS

[Uji] Method = 'lstsq' (Least Square (NumPy))
      Gateway berhasil dipanggil.
      ...
      Tipe Pasut Terdeteksi : Mixed, mainly semi-diurnal
      Formzahl              : 0.6234
      RMSE                  : 0.0187
      >> Status: LULUS

--- Ringkasan ---
SEMUA TES LULUS.
```

---

## 📊 Data Format

### Input CSV/TXT
```
time,height
01-07-2026 00:00,1.95
01-07-2026 01:00,1.88
01-07-2026 02:00,1.75
...
```

**Format Waktu Support:**
- `DD-MM-YYYY HH:MM`
- `DD-MM-YYYY HH:MM:SS`
- `YYYY-MM-DD HH:MM`
- `YYYY-MM-DD HH:MM:SS`
- `MM-DD-YYYY HH:MM`

### Output Excel Sheets
1. **Summary** - Formzahl, Tipe, RMSE
2. **Constituents** - Name, Amplitude, Phase, Speed
3. **Important Levels** - HWS, MHWS, MHWL, MSL, MLWL, MLWS, LWS
4. **Levels Report** - Format teks standar Admiralty
5. **Prediction** - Kolom time, height (1 tahun)

---

## 🔧 Konfigurasi

### LSTSQEngine Default Constituents
```python
constit_list = ['M2', 'S2', 'K1', 'O1']  # Default
```

**Custom:**
```python
from engine.lstsq_engine import LSTSQEngine
engine = LSTSQEngine(constit_list=['M2', 'S2', 'N2', 'K1', 'O1', 'M4'])
result = engine.run_analysis(df)
```

**Available Constituents:**
- M2, S2, N2, K1, O1, M4, K2, P1

---

## 📈 Formzahl & Tipe Pasut

```
Formzahl = (K1 + O1) / (M2 + S2)

Formzahl < 0.25       → Semi-Diurnal
0.25 ≤ Formzahl < 1.5 → Mixed, mainly semi-diurnal
1.5 ≤ Formzahl < 3.0  → Mixed, mainly diurnal
Formzahl ≥ 3.0        → Diurnal
```

---

## 🎯 Troubleshooting

| Error | Solusi |
|-------|--------|
| `FileNotFoundError: File tidak ditemukan` | Pastikan path file benar |
| `Data terlalu sedikit (minimal 50)` | Gunakan data minimal 50 titik (2+ hari) |
| `Tidak cukup variasi data` | Cek data pasut memiliki variasi signifikan |
| `ImportError: No module named 'utide'` | `pip install utide` (jika ingin OLS) |
| `ImportError: No module named 'PyQt6'` | `pip install PyQt6` |

---

## 📝 References

- **Admiralty Method**: UK Hydrographic Office Standards
- **UTide**: Codfish & Rich (2016) - MATLAB Harmonic Analysis Package
- **NumPy lstsq**: https://numpy.org/doc/stable/reference/generated/numpy.linalg.lstsq.html

---

## Developer
**dhanyxyz1-atl**

---

## 📄 License
Open Source - Use freely for research & education
