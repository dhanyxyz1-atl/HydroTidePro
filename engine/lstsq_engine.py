import numpy as np
import pandas as pd
from engine.levels import compute_important_levels


class LSTSQEngine:

    # Frekuensi lengkap sesuai referensi Tide_Analysis.xlsx (degrees per hour)
    CONSTITUENTS = {
        "MSF":  1.0158958,
        "O1":   13.9429539,
        "P1":   14.9589333,
        "K1":   15.0410686,
        "M2":   28.9841042,
        "S2":   30.0000000,
        "K2":   30.0821373,
        "M3":   43.4761563,
        "SK3":  45.0000000,
        "M4":   57.9682084,
        "MS4":  58.9841042,
        "S4":   60.0000000,
        "2MK5": 72.0251729,
        "2SK5": 75.0000000,
        "M6":   86.9523126,
        "2MS6": 87.9682084,
        "2SM6": 91.0158958,
        "3MK7": 101.0092771,
        "M8":   115.9364168,
    }

    _DEFAULT_CONSTIT = [
        'MSF', 'O1', 'P1', 'K1',
        'M2', 'S2', 'K2',
        'M3', 'SK3',
        'M4', 'MS4', 'S4',
        '2MK5', '2SK5',
        'M6', '2MS6', '2SM6',
        '3MK7', 'M8'
    ]

    def __init__(self, constit_list=None):
        self.constit_list = constit_list if constit_list else self._DEFAULT_CONSTIT
        self.coef = None
        self._start_time = None

    def run_analysis(self, df):
        df = df.sort_values('time').drop_duplicates(subset='time').reset_index(drop=True)

        if len(df) < 50:
            raise ValueError("Data terlalu sedikit (minimal 50 data points).")

        self._start_time = df['time'].iloc[0]

        t_hours = self._time_to_hours(df['time'])
        heights = df['height'].values

        A = self._build_design_matrix(t_hours)
        x, _, _, _ = np.linalg.lstsq(A, heights, rcond=None)
        self.coef = x

        constituents = self._extract_constituents(x)

        def get_val(name):
            res = constituents.loc[constituents['Name'] == name, 'Amplitude']
            return res.values[0] if not res.empty else 0

        k1, o1, m2, s2 = get_val('K1'), get_val('O1'), get_val('M2'), get_val('S2')
        divisor = (m2 + s2)
        formzahl = (k1 + o1) / divisor if divisor != 0 else 0

        if formzahl < 0.25:
            tipe = "Semi-Diurnal"
        elif formzahl < 1.5:
            tipe = "Mixed, mainly semi-diurnal"
        elif formzahl < 3.0:
            tipe = "Mixed, mainly diurnal"
        else:
            tipe = "Diurnal"

        year_hours = pd.date_range(start=self._start_time, periods=8760, freq='h')
        predicted_curve = self.reconstruct(year_hours)
        levels = compute_important_levels(year_hours, predicted_curve)

        predicted_obs = self.reconstruct(df['time'])
        rmse = np.sqrt(np.mean((heights - predicted_obs) ** 2))

        return {
            "constituents": constituents,
            "formzahl": formzahl,
            "type": tipe,
            "levels": levels,
            "rmse": rmse,
            "start_time": self._start_time,  # untuk waktu prediksi di GUI
            "reconstructor": self
        }

    def _time_to_hours(self, time_array):
        time_series = pd.to_datetime(pd.Series(time_array)).reset_index(drop=True)
        if len(time_series) == 0:
            raise ValueError("Array waktu kosong.")
        if self._start_time is None:
            self._start_time = time_series.iloc[0]
        delta = time_series - pd.to_datetime(self._start_time)
        return delta.dt.total_seconds().values / 3600.0

    def _build_design_matrix(self, t_hours):
        n = len(t_hours)
        cols = [np.ones(n)]
        for name in self.constit_list:
            freq_rad = np.radians(self.CONSTITUENTS[name])
            cols.append(np.cos(freq_rad * t_hours))
            cols.append(np.sin(freq_rad * t_hours))
        return np.column_stack(cols)

    def _extract_constituents(self, x):
        rows = [{'Name': 'Z0', 'Amplitude': x[0], 'Phase': 0.0, 'Speed': 0.0}]
        idx = 1
        for name in self.constit_list:
            a = x[idx]
            b = x[idx + 1]
            idx += 2
            amplitude = np.sqrt(a**2 + b**2)
            phase = np.degrees(np.arctan2(b, a))
            if phase < 0:
                phase += 360
            rows.append({
                'Name': name,
                'Amplitude': amplitude,
                'Phase': phase,
                'Speed': self.CONSTITUENTS[name],
            })
        return pd.DataFrame(rows)

    def reconstruct(self, time_array, constituents=None):
        if self.coef is None:
            raise ValueError("Belum ada analisis. Jalankan run_analysis() dulu.")
        t_hours = self._time_to_hours(time_array)
        A = self._build_design_matrix(t_hours)
        return A @ self.coef


def run_lstsq_engine(df, constit_list=None):
    return LSTSQEngine(constit_list=constit_list).run_analysis(df)