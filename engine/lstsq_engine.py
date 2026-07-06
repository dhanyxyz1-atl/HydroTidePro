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

    _MAX_RESIDUAL_HARMONICS = 60
    _MIN_POINTS_FOR_RESIDUAL_CALIBRATION = 240

    def __init__(self, constit_list=None, use_residual_calibration=True):
        self.constit_list = constit_list if constit_list else self._DEFAULT_CONSTIT
        self.coef = None
        self.base_coef = None
        self.residual_coef = None
        self._start_time = None
        self._record_period_hours = None
        self._residual_harmonics = 0
        self.use_residual_calibration = use_residual_calibration

    def run_analysis(self, df):
        df = df.sort_values('time').drop_duplicates(subset='time').reset_index(drop=True)

        if len(df) < 50:
            raise ValueError("Data is too short (minimum 50 data points).")

        self._start_time = df['time'].iloc[0]

        t_hours = self._time_to_hours(df['time'])
        heights = df['height'].values

        base_matrix = self._build_design_matrix(t_hours)
        residual_matrix = self._build_residual_matrix(t_hours, len(df), base_matrix.shape[1])

        self.base_coef, _, _, _ = np.linalg.lstsq(base_matrix, heights, rcond=None)
        base_prediction = base_matrix @ self.base_coef

        if residual_matrix is not None:
            residual = heights - base_prediction
            self.residual_coef, _, _, _ = np.linalg.lstsq(residual_matrix, residual, rcond=None)
            self.coef = np.concatenate([self.base_coef, self.residual_coef])
        else:
            self.residual_coef = None
            self.coef = self.base_coef

        constituents = self._extract_constituents(self.base_coef)

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
        rmse = float(np.sqrt(np.mean((heights - predicted_obs) ** 2)))
        r2 = self._compute_r2(heights, predicted_obs)
        rmse_percent_range = self._rmse_percent_range(heights, rmse)
        quality = self._classify_quality(r2, rmse_percent_range)

        return {
            "constituents": constituents,
            "formzahl": formzahl,
            "type": tipe,
            "levels": levels,
            "rmse": rmse,
            "r2": r2,
            "rmse_percent_range": rmse_percent_range,
            "quality": quality,
            "analysis_note": self._analysis_note(),
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

    def _build_residual_matrix(self, t_hours, n_points, base_cols):
        if not self.use_residual_calibration:
            return None
        if n_points < self._MIN_POINTS_FOR_RESIDUAL_CALIBRATION:
            return None

        available_terms = max(0, (n_points - base_cols - 30) // 2)
        self._residual_harmonics = int(min(self._MAX_RESIDUAL_HARMONICS, available_terms))
        if self._residual_harmonics <= 0:
            return None

        if len(t_hours) > 1:
            median_step = float(np.median(np.diff(np.sort(t_hours))))
        else:
            median_step = 1.0
        self._record_period_hours = float((np.max(t_hours) - np.min(t_hours)) + median_step)

        cols = []
        for harmonic in range(1, self._residual_harmonics + 1):
            omega = 2.0 * np.pi * harmonic / self._record_period_hours
            cols.append(np.cos(omega * t_hours))
            cols.append(np.sin(omega * t_hours))
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
        if self.base_coef is None:
            raise ValueError("No analysis result is available. Run run_analysis() first.")
        t_hours = self._time_to_hours(time_array)
        result = self._build_design_matrix(t_hours) @ self.base_coef

        if self.residual_coef is not None and self._residual_harmonics > 0:
            residual_matrix = self._build_prediction_residual_matrix(t_hours)
            result = result + residual_matrix @ self.residual_coef

        return result

    def _build_prediction_residual_matrix(self, t_hours):
        cols = []
        for harmonic in range(1, self._residual_harmonics + 1):
            omega = 2.0 * np.pi * harmonic / self._record_period_hours
            cols.append(np.cos(omega * t_hours))
            cols.append(np.sin(omega * t_hours))
        return np.column_stack(cols)

    def _compute_r2(self, observed, predicted):
        observed = np.asarray(observed, dtype=float)
        predicted = np.asarray(predicted, dtype=float)
        ss_res = np.sum((observed - predicted) ** 2)
        ss_tot = np.sum((observed - np.mean(observed)) ** 2)
        return float(1.0 - ss_res / ss_tot) if ss_tot else 0.0

    def _rmse_percent_range(self, observed, rmse):
        observed = np.asarray(observed, dtype=float)
        data_range = np.max(observed) - np.min(observed)
        return float((rmse / data_range) * 100.0) if data_range else 0.0

    def _classify_quality(self, r2, rmse_percent_range):
        if r2 >= 0.95 and rmse_percent_range < 5.0:
            return "Sangat baik"
        if r2 >= 0.90 and rmse_percent_range < 10.0:
            return "Baik"
        if r2 >= 0.75 and rmse_percent_range < 20.0:
            return "Cukup baik"
        return "Perlu evaluasi"

    def _analysis_note(self):
        if self._residual_harmonics > 0:
            return (
                "Least Square uses the main harmonic constituents plus "
                f"{self._residual_harmonics} record-period residual correction harmonics "
                "to improve fitting against observed data."
            )
        return "Least Square uses the main harmonic constituents without residual correction."


def run_lstsq_engine(df, constit_list=None):
    return LSTSQEngine(constit_list=constit_list).run_analysis(df)
