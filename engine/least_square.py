import utide
import pandas as pd
import numpy as np
from matplotlib.dates import date2num
from engine.levels import compute_important_levels


class LeastSquareEngine:
    _DEFAULT_LAT = -6.97  # konstanta internal, GANTI sesuai lokasi asli jika diketahui

    # Daftar konstituen eksplisit (sama seperti hasil referensi Tide_Analysis.xlsx),
    # dipaksa manual supaya tidak bergantung pada auto-selection UTide yang
    # bisa gagal/flat saat conf_int dimatikan. Z0 (mean level) selalu
    # otomatis disertakan oleh UTide tanpa perlu disebut di sini.
    _CONSTIT_LIST = [
        'MSF', 'O1', 'P1', 'K1', 'M2', 'S2', 'K2',
        'M3', 'SK3', 'M4', 'MS4', 'S4',
        '2MK5', '2SK5', 'M6', '2MS6', '2SM6', '3MK7', 'M8'
    ]

    def __init__(self):
        self.coef = None

    def run_analysis(self, df):
        df = df.sort_values('time').drop_duplicates(subset='time').reset_index(drop=True)

        if len(df) < 50:
            raise ValueError("Data terlalu sedikit untuk analisis harmonik (minimal puluhan baris).")

        time_num = date2num(df['time'])

        coef = utide.solve(
            time_num, df['height'].values,
            lat=self._DEFAULT_LAT,
            method='ols',
            conf_int='none',
            trend=False,
            constit=self._CONSTIT_LIST,
            verbose=False
        )
        self.coef = coef

        speed_deg_per_hour = np.asarray(coef.aux.frq) * 360.0

        constituents = pd.DataFrame({
            'Name': coef.name,
            'Amplitude': coef.A,
            'Phase': coef.g,
            'Speed': speed_deg_per_hour
        })

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

        year_hours = pd.date_range(start=df['time'].iloc[0], periods=8760, freq='h')
        predicted_curve = self.reconstruct(year_hours, constituents)
        levels = compute_important_levels(year_hours, predicted_curve)

        return {
            "constituents": constituents,
            "formzahl": formzahl,
            "type": tipe,
            "levels": levels,
            "rmse": coef.rms if hasattr(coef, 'rms') else None,
            "reconstructor": self
        }

    def reconstruct(self, time_array, constituents=None):
        if self.coef is None:
            raise ValueError("Belum ada hasil analisis (coef kosong). Jalankan run_analysis() dulu.")

        time_num = date2num(pd.to_datetime(pd.Series(time_array)))
        recon = utide.reconstruct(time_num, self.coef, verbose=False)
        return recon.h


def run_least_square(df):
    return LeastSquareEngine().run_analysis(df)