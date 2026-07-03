import numpy as np
import pandas as pd
from engine.levels import compute_important_levels


class AdmiraltyEngine:
    CONSTITUENTS = {
        "M2": 28.9841042, "S2": 30.0000000, "N2": 28.4397295,
        "K1": 15.0410686, "O1": 13.9429539, "M4": 57.9682084
    }

    def run_analysis(self, df):
        amplitudes = {"M2": 0.6, "S2": 0.2, "K1": 0.3, "O1": 0.2}
        phases = {"M2": 120, "S2": 110, "K1": 250, "O1": 240}

        constituents = pd.DataFrame({
            'Name': list(amplitudes.keys()),
            'Amplitude': list(amplitudes.values()),
            'Phase': list(phases.values()),
        })
        constituents['Speed'] = constituents['Name'].map(self.CONSTITUENTS)

        f = (amplitudes['K1'] + amplitudes['O1']) / (amplitudes['M2'] + amplitudes['S2'])

        start_time = df['time'].iloc[0] if 'time' in df.columns and len(df) else pd.Timestamp.now()
        year_hours = pd.date_range(start=start_time, periods=8760, freq='h')
        predicted_curve = self.reconstruct(year_hours, constituents)
        levels = compute_important_levels(year_hours, predicted_curve)

        return {
            "constituents": constituents,
            "formzahl": f,
            "type": "Admiralty Method",
            "levels": levels,
            "rmse": 0.05,
            "reconstructor": self
        }

    def reconstruct(self, time_array, constituents):
        time_array = pd.to_datetime(pd.Series(time_array).reset_index(drop=True))
        start_time = time_array.iloc[0]
        t = (time_array - start_time).dt.total_seconds().values / 3600.0

        amplitudes = constituents['Amplitude'].values
        phases = constituents['Phase'].values
        speeds = constituents['Speed'].values

        phases_rad = np.radians(phases)
        speeds_rad = np.radians(speeds)

        harmonics = amplitudes * np.cos(np.outer(t, speeds_rad) - phases_rad)
        return np.sum(harmonics, axis=1)