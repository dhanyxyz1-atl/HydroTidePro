"""
LeastSquareEngine dengan numpy.linalg.lstsq
Analisis harmonik pasut menggunakan curve fitting least squares langsung.
"""

import numpy as np
import pandas as pd
from matplotlib.dates import date2num
from engine.levels import compute_important_levels


class LSTSQEngine:
    """
    Engine analisis pasut menggunakan numpy.linalg.lstsq.
    
    Konsep:
    - Data pasut = kombinasi linier dari komponen harmonik
    - h(t) = Z0 + A1*cos(ω1*t - φ1) + A2*cos(ω2*t - φ2) + ...
    
    Merubah ke bentuk linier:
    h(t) = c0 + sum(a_i * cos(ωi*t) + b_i * sin(ωi*t))
    
    Kemudian gunakan lstsq untuk cari koefisien optimal.
    """
    
    # Frekuensi konstituen utama (degrees per hour)
    CONSTITUENTS = {
        "M2": 28.9841042,    # Semi-diurnal bulan
        "S2": 30.0000000,    # Semi-diurnal matahari
        "N2": 28.4397295,    # Semi-diurnal bulan (elliptic)
        "K1": 15.0410686,    # Diurnal (lunisolar)
        "O1": 13.9429539,    # Diurnal (lunar)
        "M4": 57.9682084,    # Overtide (M2*2)
        "K2": 30.0821373,    # Semi-diurnal (lunisolar)
        "P1": 14.9589333,    # Diurnal (solar)
    }
    
    _DEFAULT_LAT = -6.97

    def __init__(self, constit_list=None):
        """
        Args:
            constit_list: List nama konstituen yang digunakan.
                         Default: ['M2', 'S2', 'K1', 'O1']
        """
        if constit_list is None:
            constit_list = ['M2', 'S2', 'K1', 'O1']
        
        self.constit_list = constit_list
        self.coef = None
        self.residuals = None
        self.rank = None
        self.singular_values = None

    def run_analysis(self, df):
        """
        Jalankan analisis pasut dengan least squares.
        
        Args:
            df: DataFrame dengan kolom 'time' dan 'height'
            
        Returns:
            dict dengan keys: constituents, formzahl, type, levels, rmse, reconstructor
        """
        df = df.sort_values('time').drop_duplicates(subset='time').reset_index(drop=True)

        if len(df) < 50:
            raise ValueError("Data terlalu sedikit untuk analisis (minimal 50 data points).")

        # Konversi waktu ke jam dari epoch
        t_hours = self._time_to_hours(df['time'].values)
        heights = df['height'].values

        # Build design matrix A
        A = self._build_design_matrix(t_hours)

        # Solve least squares: A @ x = heights
        # lstsq mengembalikan: (x, residuals, rank, s)
        x, residuals_lstsq, rank, s = np.linalg.lstsq(A, heights, rcond=None)

        self.coef = x
        self.residuals = residuals_lstsq
        self.rank = rank
        self.singular_values = s

        # Extract Z0 (mean level) dan amplitudes/phases untuk setiap konstituen
        constituents = self._extract_constituents(x)

        # Hitung formzahl
        k1 = constituents.loc[constituents['Name'] == 'K1', 'Amplitude'].values[0] if 'K1' in constituents['Name'].values else 0
        o1 = constituents.loc[constituents['Name'] == 'O1', 'Amplitude'].values[0] if 'O1' in constituents['Name'].values else 0
        m2 = constituents.loc[constituents['Name'] == 'M2', 'Amplitude'].values[0] if 'M2' in constituents['Name'].values else 0
        s2 = constituents.loc[constituents['Name'] == 'S2', 'Amplitude'].values[0] if 'S2' in constituents['Name'].values else 0

        divisor = (m2 + s2)
        formzahl = (k1 + o1) / divisor if divisor != 0 else 0

        # Klasifikasi tipe pasut
        if formzahl < 0.25:
            tipe = "Semi-Diurnal"
        elif formzahl < 1.5:
            tipe = "Mixed, mainly semi-diurnal"
        elif formzahl < 3.0:
            tipe = "Mixed, mainly diurnal"
        else:
            tipe = "Diurnal"

        # Prediksi 1 tahun untuk hitung levels
        year_hours = pd.date_range(start=df['time'].iloc[0], periods=8760, freq='h')
        predicted_curve = self.reconstruct(year_hours)
        levels = compute_important_levels(year_hours, predicted_curve)

        # Hitung RMSE
        predicted = self.reconstruct(df['time'])
        rmse = np.sqrt(np.mean((heights - predicted) ** 2))

        return {
            "constituents": constituents,
            "formzahl": formzahl,
            "type": tipe,
            "levels": levels,
            "rmse": rmse,
            "reconstructor": self
        }

    def _time_to_hours(self, time_array):
        """Konversi time array ke jam dari start time."""
        time_series = pd.to_datetime(time_array)
        start_time = time_series.iloc[0]
        t_hours = (time_series - start_time).dt.total_seconds().values / 3600.0
        return t_hours

    def _build_design_matrix(self, t_hours):
        """
        Build design matrix untuk least squares.
        
        Model: h(t) = Z0 + sum(a_i * cos(ωi*t) + b_i * sin(ωi*t))
        
        Columns: [1, cos(ω1*t), sin(ω1*t), cos(ω2*t), sin(ω2*t), ...]
        """
        n = len(t_hours)
        cols = [np.ones(n)]  # Z0 (mean level)

        # Konversi frekuensi dari degrees/hour ke radians/hour
        for name in self.constit_list:
            freq_deg = self.CONSTITUENTS[name]
            freq_rad = np.radians(freq_deg)
            
            # cos dan sin komponen
            cols.append(np.cos(freq_rad * t_hours))
            cols.append(np.sin(freq_rad * t_hours))

        A = np.column_stack(cols)
        return A

    def _extract_constituents(self, x):
        """
        Extract amplitude dan phase dari koefisien least squares.
        
        x[0] = Z0
        x[2i-1] = a_i (cos coeff)
        x[2i]   = b_i (sin coeff)
        
        Amplitude: A_i = sqrt(a_i^2 + b_i^2)
        Phase: φ_i = atan2(b_i, a_i) [dalam degrees]
        """
        data = []
        data.append({
            'Name': 'Z0',
            'Amplitude': x[0],
            'Phase': 0.0,
            'Speed': 0.0,
            'CosCoeff': x[0],
            'SinCoeff': 0.0
        })

        idx = 1
        for name in self.constit_list:
            a = x[idx]      # cos coefficient
            b = x[idx + 1]  # sin coefficient
            idx += 2

            amplitude = np.sqrt(a**2 + b**2)
            # Phase dalam degrees (atan2 returns radians)
            phase = np.degrees(np.arctan2(b, a))
            if phase < 0:
                phase += 360

            speed = self.CONSTITUENTS[name]

            data.append({
                'Name': name,
                'Amplitude': amplitude,
                'Phase': phase,
                'Speed': speed,
                'CosCoeff': a,
                'SinCoeff': b
            })

        return pd.DataFrame(data)

    def reconstruct(self, time_array, constituents=None):
        """
        Rekonstruksi kurva pasut menggunakan koefisien fitted.
        
        Args:
            time_array: Array waktu untuk prediksi
            constituents: DataFrame constituents (optional, untuk compatibility)
            
        Returns:
            Array tinggi air prediksi
        """
        if self.coef is None:
            raise ValueError("Belum ada analisis (coef kosong). Jalankan run_analysis() dulu.")

        t_hours = self._time_to_hours(time_array)
        
        # Reconstruct dengan design matrix dan koefisien
        A = self._build_design_matrix(t_hours)
        predicted = A @ self.coef
        
        return predicted


def run_lstsq_engine(df, constit_list=None):
    """Convenience function untuk jalankan LSTSQ engine."""
    return LSTSQEngine(constit_list=constit_list).run_analysis(df)
