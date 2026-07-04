from __future__ import annotations

from dataclasses import dataclass
from math import cos, sin, radians

import numpy as np
import pandas as pd

from engine.levels import compute_important_levels


CONSTITUENT_SPEEDS = {
    "S0": 0.0,
    "M2": 28.9841042,
    "S2": 30.0,
    "N2": 28.4397295,
    "K1": 15.0410686,
    "O1": 13.9430356,
    "M4": 57.9682084,
    "MS4": 58.9841042,
    "K2": 30.0821373,
    "P1": 14.9589314,
}


SIGN_TABLE = np.array(
    [
        [1, 1, 0, -1, 1, 1, 0],
        [1, 1, -1, -1, 1, 1, -1],
        [1, 1, -1, 1, 1, -1, -1],
        [1, 1, -1, 1, 1, -1, -1],
        [1, -1, -1, 1, 1, -1, 1],
        [1, -1, -1, 1, -1, 1, 1],
        [1, -1, -1, 1, -1, 1, 1],
        [1, -1, 0, -1, -1, 1, 0],
        [1, -1, 1, -1, -1, 1, -1],
        [1, -1, 1, -1, -1, -1, -1],
        [1, -1, 1, -1, 1, -1, -1],
        [1, 1, 1, -1, 1, -1, 1],
        [1, 1, 1, 1, 1, -1, 1],
        [1, 1, 1, 1, 1, 1, 1],
        [1, 1, 0, 1, 0, 1, 0],
        [1, 1, -1, 1, -1, 1, -1],
        [1, 1, -1, 1, -1, -1, -1],
        [1, 1, -1, -1, -1, -1, -1],
        [1, -1, -1, -1, -1, -1, 1],
        [1, -1, -1, -1, 1, -1, 1],
        [1, -1, -1, -1, 1, 1, 1],
        [1, -1, 0, -1, 1, 1, 0],
        [1, -1, 1, 1, 1, 1, -1],
        [1, -1, 1, 1, 1, 1, -1],
        [1, -1, 1, 1, -1, -1, -1],
        [1, 1, 1, 1, -1, -1, 1],
        [1, 1, 1, 1, -1, -1, 1],
        [1, 1, 1, -1, -1, 1, 1],
        [1, 1, 0, -1, -1, 1, 0],
    ],
    dtype=float,
)

NAMES = ("S0", "M2", "S2", "N2", "K1", "O1", "M4", "MS4")
P_CONSTANTS = dict(zip(NAMES, (669.0, 559.0, 448.0, 566.0, 439.0, 565.0, 507.0, 535.0)))
PHASE_P = dict(zip(NAMES, (0.0, 333.0, 345.0, 327.0, 173.0, 160.0, 307.0, 313.0)))
PHASE_CYCLES = dict(zip(NAMES, (0.0, 720.0, 360.0, 360.0, 360.0, 360.0, 360.0, 720.0)))


@dataclass
class AdmiraltyDebug:
    schema1: pd.DataFrame
    schema2: pd.DataFrame
    schema3: pd.DataFrame
    table_iv: pd.DataFrame
    pr_cos: dict[str, float]
    pr_sin: dict[str, float]
    astronomy: dict[str, dict[str, float]]


class AdmiraltyEngine:
    def __init__(self, days: int = 29):
        self.days = days
        self.constituents: pd.DataFrame | None = None
        self.reference_time: pd.Timestamp | None = None
        self.debug: AdmiraltyDebug | None = None

    def run_analysis(self, df: pd.DataFrame) -> dict:
        data = self._prepare_data(df)
        self.reference_time = data["time"].iloc[0]

        schema1 = self._build_schema1(data)
        schema2 = self._build_schema2(schema1)
        schema3 = self._build_schema3(schema2)
        table_iv = self._build_table_iv(schema3)
        aggregates = self._build_schema_iv_aggregates(table_iv)
        pr_cos, pr_sin, pr = self._compute_table_v_vi(aggregates)
        astronomy = self._compute_astronomy(data["time"].iloc[0])
        constituents = self._compute_constituents(pr_cos, pr_sin, pr, astronomy)

        self.constituents = constituents
        observed_time = data["time"].iloc[: self.days * 24]
        observed_height = data["height"].iloc[: self.days * 24].to_numpy(dtype=float)
        predicted_height = self.reconstruct(observed_time, constituents)
        rmse = float(np.sqrt(np.mean((observed_height - predicted_height) ** 2)))

        year_hours = pd.date_range(start=self.reference_time, periods=8760, freq="h")
        prediction = self.reconstruct(year_hours, constituents)
        levels = compute_important_levels(year_hours, prediction)
        formzahl = self._compute_formzahl(constituents)

        self.debug = AdmiraltyDebug(
            schema1=schema1,
            schema2=schema2,
            schema3=schema3,
            table_iv=table_iv,
            pr_cos=pr_cos,
            pr_sin=pr_sin,
            astronomy=astronomy,
        )

        return {
            "constituents": constituents,
            "formzahl": formzahl,
            "type": self._classify_tide(formzahl),
            "levels": levels,
            "rmse": rmse,
            "reconstructor": self,
        }

    def reconstruct(self, time_array, constituents: pd.DataFrame | None = None) -> np.ndarray:
        if constituents is None:
            if self.constituents is None:
                raise ValueError("Jalankan run_analysis() sebelum reconstruct().")
            constituents = self.constituents

        time_series = pd.to_datetime(pd.Series(time_array)).reset_index(drop=True)
        start_time = self.reference_time or time_series.iloc[0]
        t_hours = (time_series - start_time).dt.total_seconds().to_numpy(dtype=float) / 3600.0
        eta = np.zeros(len(t_hours), dtype=float)

        for _, row in constituents.iterrows():
            name = row["Name"]
            amplitude = float(row["Amplitude"])
            phase = float(row["Phase"])
            speed = float(row["Speed"])
            if name == "S0" or speed == 0:
                eta += amplitude
            else:
                eta += amplitude * np.cos(np.radians(speed * t_hours - phase))

        return eta

    def _prepare_data(self, df: pd.DataFrame) -> pd.DataFrame:
        if "time" not in df.columns or "height" not in df.columns:
            raise ValueError("AdmiraltyEngine membutuhkan DataFrame dengan kolom time,height.")

        data = df[["time", "height"]].copy()
        data["time"] = pd.to_datetime(data["time"], errors="coerce")
        data["height"] = pd.to_numeric(data["height"], errors="coerce")
        data = data.dropna(subset=["time", "height"])
        data = data.sort_values("time").drop_duplicates("time").reset_index(drop=True)

        if len(data) < self.days * 24:
            raise ValueError(
                f"Metode Admiralty membutuhkan minimal {self.days} hari data hourly "
                f"({self.days * 24} data). Data tersedia: {len(data)}."
            )

        return data

    def _build_schema1(self, data: pd.DataFrame) -> pd.DataFrame:
        start = data["time"].iloc[0].floor("D")
        end = start + pd.Timedelta(days=self.days)
        window = data[(data["time"] >= start) & (data["time"] < end)].copy()

        if len(window) < self.days * 24:
            raise ValueError("Data hourly tidak lengkap untuk 29 hari pertama.")

        window["day"] = (window["time"].dt.floor("D") - start).dt.days + 1
        window["hour"] = window["time"].dt.hour
        schema = window.pivot_table(index="day", columns="hour", values="height", aggfunc="mean")
        schema = schema.reindex(index=range(1, self.days + 1), columns=range(24))

        if schema.isna().any().any():
            raise ValueError("Schema I mengandung jam kosong. Pastikan data hourly lengkap.")

        return schema.astype(float)

    def _build_schema2(self, schema1: pd.DataFrame) -> pd.DataFrame:
        h = schema1.to_numpy(dtype=float)
        rows = []
        for row in h:
            z = row[6:18].sum()
            aa = row[0:6].sum() + row[18:24].sum()
            ab = row[12:24].sum()
            ac = row[0:12].sum()
            ad = row[0:3].sum() + row[9:15].sum() + row[21:24].sum()
            ae = row[3:9].sum() + row[15:21].sum()
            af = row[0:6].sum() + row[12:18].sum()
            ag = row[6:12].sum() + row[18:24].sum()
            ah = row[[0, 5, 6, 11, 12, 17, 18, 23]].sum()
            ai = row[20:22].sum() + row[14:16].sum() + row[8:10].sum() + row[2:4].sum()
            aj = row[18:21].sum() + row[12:15].sum() + row[6:9].sum() + row[0:3].sum()
            ak = row[21:24].sum() + row[15:18].sum() + row[9:12].sum() + row[3:6].sum()
            rows.append([z, aa, ab, ac, ad, ae, af, ag, ah, ai, aj, ak])

        return pd.DataFrame(
            rows,
            index=schema1.index,
            columns=["Z", "AA", "AB", "AC", "AD", "AE", "AF", "AG", "AH", "AI", "AJ", "AK"],
        )

    def _build_schema3(self, schema2: pd.DataFrame) -> pd.DataFrame:
        offset = 2000.0
        out = pd.DataFrame(index=schema2.index)
        out["AL"] = schema2["Z"] + schema2["AA"]
        out["AM"] = schema2["Z"] - schema2["AA"] + offset
        out["AN"] = schema2["AB"] - schema2["AC"] + offset
        out["AO"] = schema2["AD"] - schema2["AE"] + offset
        out["AP"] = schema2["AF"] - schema2["AG"] + offset
        out["AQ"] = schema2["AH"] - schema2["AI"] + offset
        out["AR"] = schema2["AJ"] - schema2["AK"] + offset
        return out

    def _build_table_iv(self, schema3: pd.DataFrame) -> pd.DataFrame:
        base = schema3.iloc[:29].reset_index(drop=True)
        s = SIGN_TABLE
        table = pd.DataFrame(index=range(29))
        table["AC"] = base["AL"] * s[:, 0]
        table["AD"] = base["AM"] * s[:, 0]
        table["AE"] = base["AN"] * s[:, 0]
        table["AF"] = base["AM"] * s[:, 1]
        table["AG"] = base["AN"] * s[:, 1]
        table["AH"] = base["AM"] * s[:, 2]
        table["AI"] = base["AN"] * s[:, 2]
        table["AJ"] = base["AM"] * s[:, 3]
        table["AK"] = base["AN"] * s[:, 3]
        table["AL"] = base["AM"] * s[:, 4]
        table["AM"] = base["AN"] * s[:, 4]
        table["AN"] = base["AO"] * s[:, 0]
        table["AO"] = base["AP"] * s[:, 0]
        table["AP"] = base["AO"] * s[:, 1]
        table["AQ"] = base["AP"] * s[:, 1]
        table["AR"] = base["AO"] * s[:, 2]
        table["AS"] = base["AP"] * s[:, 2]
        table["AT"] = base["AO"] * s[:, 3]
        table["AU"] = base["AP"] * s[:, 3]
        table["AV"] = base["AO"] * s[:, 4]
        table["AW"] = base["AP"] * s[:, 4]
        table["AX"] = base["AQ"] * s[:, 1]
        table["AY"] = base["AR"] * s[:, 1]
        table["AZ"] = base["AQ"] * s[:, 2]
        table["BA"] = base["AR"] * s[:, 2]
        table["BB"] = base["AQ"] * s[:, 5]
        table["BC"] = base["AR"] * s[:, 5]
        table["BD"] = base["AQ"] * s[:, 6]
        table["BE"] = base["AR"] * s[:, 6]
        return table

    def _build_schema_iv_aggregates(self, table: pd.DataFrame) -> dict[str, dict[str, float]]:
        def sr(col: str, *ranges: tuple[int, int]) -> float:
            total = 0.0
            for start_row, end_row in ranges:
                start = start_row - 57
                end = end_row - 57
                total += table[col].iloc[start : end + 1].sum()
            return float(total)

        offset = 2000.0
        x_raw = {
            "00": sr("AC", (57, 85)),
            "10": sr("AD", (57, 85)),
            "12": sr("AF", (57, 60), (68, 74), (82, 85)),
            "1b": sr("AH", (65, 70), (79, 84)),
            "13": sr("AJ", (59, 63), (69, 73), (79, 83)),
            "1c": sr("AL", (57, 61), (67, 70), (76, 80)),
            "20": sr("AN", (57, 85)),
            "22": sr("AP", (57, 60), (68, 74), (82, 85)),
            "2b": sr("AR", (65, 70), (79, 84)),
            "23": sr("AT", (59, 63), (69, 73), (79, 83)),
            "2c": sr("AV", (57, 61), (67, 70), (76, 80)),
            "42": sr("AX", (57, 60), (68, 74), (82, 85)),
            "4b": sr("AZ", (65, 70), (79, 84)),
            "44": sr("BB", (57, 58), (62, 65), (70, 72), (77, 80), (84, 85)),
            "4d": sr("BD", (61, 63), (68, 70), (75, 77), (82, 84)),
        }
        y_raw = {
            "10": sr("AE", (57, 85)),
            "12": sr("AG", (57, 60), (68, 74), (82, 85)),
            "1b": sr("AI", (65, 70), (79, 84)),
            "13": sr("AK", (59, 63), (69, 73), (79, 83)),
            "1c": sr("AM", (57, 61), (67, 70), (76, 80)),
            "20": sr("AO", (57, 85)),
            "22": sr("AQ", (57, 60), (68, 74), (82, 85)),
            "2b": sr("AS", (65, 70), (79, 84)),
            "23": sr("AU", (59, 63), (69, 73), (79, 83)),
            "2c": sr("AW", (57, 61), (67, 70), (76, 80)),
            "42": sr("AY", (57, 60), (68, 74), (82, 85)),
            "4b": sr("BA", (65, 70), (79, 84)),
            "44": sr("BC", (57, 58), (62, 65), (70, 72), (77, 80), (84, 85)),
            "4d": sr("BE", (61, 63), (68, 70), (75, 77), (82, 84)),
        }

        x = {
            "00": x_raw["00"],
            "10": x_raw["10"] - offset * 29.0,
            "12": x_raw["12"] + sr("AF", (61, 67), (75, 81)) - offset,
            "1b": x_raw["1b"] + sr("AH", (58, 63), (72, 77)),
            "13": x_raw["13"] + sr("AJ", (57, 58), (64, 68), (74, 78), (84, 85)) - offset,
            "1c": x_raw["1c"] + sr("AL", (62, 66), (72, 75), (81, 85)),
            "20": x_raw["20"] - offset * 29.0,
            "22": x_raw["22"] + sr("AP", (61, 67), (75, 81)) - offset,
            "2b": x_raw["2b"] + sr("AR", (58, 63), (72, 77)),
            "23": x_raw["23"] + sr("AT", (57, 58), (64, 68), (74, 78), (84, 85)) - offset,
            "2c": x_raw["2c"] + sr("AV", (62, 66), (72, 75), (81, 85)),
            "42": x_raw["42"] + sr("AX", (61, 67), (75, 81)) - offset,
            "4b": x_raw["4b"] + sr("AZ", (58, 63), (72, 77)),
            "44": x_raw["44"] + sr("BB", (59, 61), (66, 69), (73, 76), (81, 83)) - offset,
            "4d": x_raw["4d"] + sr("BD", (58, 60), (65, 67), (72, 74), (79, 81)),
        }
        y = {
            "10": y_raw["10"] - offset * 29.0,
            "12": y_raw["12"] + sr("AG", (61, 67), (75, 81)) - offset,
            "1b": y_raw["1b"] + sr("AI", (58, 63), (72, 77)),
            "13": y_raw["13"] + sr("AK", (57, 58), (64, 68), (74, 78), (84, 85)) - offset,
            "1c": y_raw["1c"] + sr("AM", (62, 66), (72, 75), (81, 85)),
            "20": y_raw["20"] - offset * 29.0,
            "22": y_raw["22"] + sr("AQ", (61, 67), (75, 81)) - offset,
            "2b": y_raw["2b"] + sr("AS", (58, 63), (72, 77)),
            "23": y_raw["23"] + sr("AU", (57, 58), (64, 68), (74, 78), (84, 85)) - offset,
            "2c": y_raw["2c"] + sr("AW", (62, 66), (72, 75), (81, 85)),
            "42": y_raw["42"] + sr("AY", (61, 67), (75, 81)) - offset,
            "4b": y_raw["4b"] + sr("BA", (58, 63), (72, 77)),
            "44": y_raw["44"] + sr("BC", (59, 61), (66, 69), (73, 76), (81, 83)) - offset,
            "4d": y_raw["4d"] + sr("BE", (58, 60), (65, 67), (72, 74), (79, 81)),
        }
        return {"x": x, "y": y}

    def _compute_table_v_vi(
        self, aggregates: dict[str, dict[str, float]]
    ) -> tuple[dict[str, float], dict[str, float], dict[str, float]]:
        x = aggregates["x"]
        y = aggregates["y"]
        cos_rows = {
            "X00": x["00"],
            "X10": x["10"],
            "X12Y1b": x["12"] - y["1b"],
            "X13Y1c": x["13"] - y["1c"],
            "X20": x["20"],
            "X22Y2b": x["22"] - y["2b"],
            "X23Y2c": x["23"] - y["2c"],
            "X42Y4b": x["42"] - y["4b"],
            "X44Y4d": x["44"] - y["4d"],
        }
        sin_rows = {
            "Y10": y["10"],
            "Y12X1b": y["12"] + x["1b"],
            "Y13X1c": y["13"] + x["1c"],
            "Y20": y["20"],
            "Y22X2b": y["22"] + x["2b"],
            "Y23X2c": y["23"] + x["2c"],
            "Y42X4b": y["42"] + x["4b"],
            "Y44X4d": y["44"] + x["4d"],
        }

        pr_cos = dict.fromkeys(NAMES, 0.0)
        pr_sin = dict.fromkeys(NAMES, 0.0)
        pr_cos["S0"] += cos_rows["X00"]
        pr_cos["K1"] += cos_rows["X10"]
        pr_cos["O1"] += -0.08 * cos_rows["X10"]
        pr_cos["M2"] += 0.07 * cos_rows["X12Y1b"]
        pr_cos["K1"] += -0.02 * cos_rows["X12Y1b"]
        pr_cos["O1"] += cos_rows["X12Y1b"]
        pr_cos["MS4"] += 0.02 * cos_rows["X12Y1b"]
        pr_cos["M2"] += -0.03 * cos_rows["X20"]
        pr_cos["S2"] += cos_rows["X20"]
        pr_cos["N2"] += -0.03 * cos_rows["X20"]
        pr_cos["M2"] += cos_rows["X22Y2b"]
        pr_cos["S2"] += 0.015 * cos_rows["X22Y2b"]
        pr_cos["N2"] += 0.038 * cos_rows["X22Y2b"]
        pr_cos["K1"] += 0.002 * cos_rows["X22Y2b"]
        pr_cos["O1"] += -0.058 * cos_rows["X22Y2b"]
        pr_cos["MS4"] += -0.035 * cos_rows["X22Y2b"]
        pr_cos["M2"] += -0.06 * cos_rows["X23Y2c"]
        pr_cos["N2"] += cos_rows["X23Y2c"]
        pr_cos["M2"] += 0.03 * cos_rows["X42Y4b"]
        pr_cos["MS4"] += cos_rows["X42Y4b"]
        pr_cos["M4"] += cos_rows["X44Y4d"]
        pr_cos["MS4"] += 0.08 * cos_rows["X44Y4d"]

        pr_sin["K1"] += sin_rows["Y10"]
        pr_sin["O1"] += -0.08 * sin_rows["Y10"]
        pr_sin["M2"] += 0.07 * sin_rows["Y12X1b"]
        pr_sin["K1"] += -0.02 * sin_rows["Y12X1b"]
        pr_sin["O1"] += sin_rows["Y12X1b"]
        pr_sin["MS4"] += 0.03 * sin_rows["Y12X1b"]
        pr_sin["M2"] += -0.03 * sin_rows["Y20"]
        pr_sin["S2"] += sin_rows["Y20"]
        pr_sin["N2"] += -0.03 * sin_rows["Y20"]
        pr_sin["M2"] += sin_rows["Y22X2b"]
        pr_sin["S2"] += 0.015 * sin_rows["Y22X2b"]
        pr_sin["N2"] += 0.032 * sin_rows["Y22X2b"]
        pr_sin["O1"] += -0.057 * sin_rows["Y22X2b"]
        pr_sin["MS4"] += -0.035 * sin_rows["Y22X2b"]
        pr_sin["M2"] += -0.06 * sin_rows["Y23X2c"]
        pr_sin["N2"] += sin_rows["Y23X2c"]
        pr_sin["M2"] += 0.03 * sin_rows["Y42X4b"]
        pr_sin["M4"] += 0.01 * sin_rows["Y42X4b"]
        pr_sin["MS4"] += sin_rows["Y42X4b"]
        pr_sin["M4"] += sin_rows["Y44X4d"]
        pr_sin["MS4"] += 0.08 * sin_rows["Y44X4d"]

        pr = {name: float(np.hypot(pr_cos[name], pr_sin[name])) for name in NAMES}
        return pr_cos, pr_sin, pr

    def _compute_astronomy(self, start_time: pd.Timestamp) -> dict[str, dict[str, float]]:
        mid_time = pd.Timestamp(start_time).floor("D") + pd.Timedelta(days=14)
        year = float(mid_time.year)
        day_number = float(mid_time.dayofyear)
        leap_term = (year - 1901.0) / 4.0

        s = 277.025 + 129.38481 * (year - 1900.0) + 13.1764 * (day_number + leap_term)
        h = 280.19 - 0.23872 * (year - 1900.0) + 0.98565 * (day_number + leap_term)
        p = 334.385 + 40.66249 * (year - 1900.0) + 0.1114 * (day_number + leap_term)
        n_node = 259.157 - 19.32818 * (year - 1900.0) - 0.05295 * (day_number + leap_term)
        n_rad = radians(n_node)

        f = {
            "S0": 1.0,
            "M2": 1.0004 - 0.0373 * cos(n_rad) + 0.0002 * cos(2 * n_rad),
            "S2": 1.0,
            "K2": 1.0241 + 0.2863 * cos(n_rad) + 0.0083 * cos(2 * n_rad) - 0.0015 * cos(3 * n_rad),
            "O1": 1.0089 + 0.1871 * cos(n_rad) - 0.0147 * cos(2 * n_rad) + 0.0014 * cos(3 * n_rad),
            "K1": 1.006 + 0.115 * cos(n_rad) - 0.0088 * cos(2 * n_rad) + 0.0006 * cos(3 * n_rad),
            "P1": 1.0,
        }
        f["N2"] = f["M2"]
        f["M4"] = f["M2"] ** 2
        f["MS4"] = f["M2"]

        u = {
            "S0": 0.0,
            "M2": -2.14 * sin(n_rad),
            "S2": 0.0,
            "K2": -17.74 * sin(n_rad) + 0.68 * sin(2 * n_rad) - 0.04 * sin(3 * n_rad),
            "K1": -8.86 * sin(n_rad) + 0.68 * sin(2 * n_rad) - 0.07 * sin(3 * n_rad),
            "O1": 10.8 * sin(n_rad) - 1.34 * sin(2 * n_rad) + 0.19 * sin(3 * n_rad),
            "P1": 0.0,
        }
        u["N2"] = u["M2"]
        u["M4"] = 2.0 * u["M2"]
        u["MS4"] = u["M2"]

        v_raw = {
            "M2": -2.0 * s + 2.0 * h,
            "K1": h + 90.0,
            "O1": -2.0 * s + h + 270.0,
            "K2": 2.0 * h,
            "S2": 0.0,
            "P1": -h + 270.0,
            "N2": -3.0 * s + 2.0 * h + p,
        }
        v_raw["M4"] = 2.0 * v_raw["M2"]
        v_raw["MS4"] = v_raw["M2"]
        v_raw["S0"] = 0.0
        v = {name: _positive_degrees(value) for name, value in v_raw.items()}

        return {"f": f, "u": u, "V": v, "raw": {"s": s, "h": h, "p": p, "N": n_node}}

    def _compute_constituents(
        self,
        pr_cos: dict[str, float],
        pr_sin: dict[str, float],
        pr: dict[str, float],
        astronomy: dict[str, dict[str, float]],
    ) -> pd.DataFrame:
        f = astronomy["f"]
        u = astronomy["u"]
        v = astronomy["V"]
        r = {name: _positive_degrees(np.degrees(np.arctan2(pr_sin[name], pr_cos[name]))) for name in NAMES}

        k2_f = f["K2"]
        k1_f = f["K1"]
        s2_sum = v["K1"] + u["K1"]
        s2_w_over_f = _linear(s2_sum, 280.0, 290.0, 6.9, 10.8)
        s2_w_factor = _linear(s2_sum, 280.0, 290.0, 0.265, 0.241)
        s2_w = s2_w_over_f * k2_f
        s2_one_plus_w = 1.0 + s2_w_factor * k2_f

        k1_sum = (2.0 * v["K1"] + u["K1"]) - 360.0
        k1_wf = _linear(k1_sum, 220.0, 230.0, 15.9, 17.8)
        k1_w_factor = _linear(k1_sum, 220.0, 230.0, -0.224, -0.173)
        k1_w = k1_wf / k1_f
        k1_one_plus_w = 1.0 + k1_w_factor / k1_f

        n2_diff = (3.0 * v["M2"]) - (2.0 * v["N2"])
        n2_w = _linear(n2_diff, 230.0, 240.0, -9.1, -10.0)
        n2_one_plus_w = _linear(n2_diff, 230.0, 240.0, 0.893, 0.922)

        w = {"S0": 0.0, "M2": 0.0, "S2": s2_w, "N2": n2_w, "K1": k1_w, "O1": 0.0, "M4": 0.0, "MS4": s2_w}
        one_plus_w = {
            "S0": 1.0,
            "M2": 1.0,
            "S2": s2_one_plus_w,
            "N2": n2_one_plus_w,
            "K1": k1_one_plus_w,
            "O1": 1.0,
            "M4": 1.0,
            "MS4": s2_one_plus_w,
        }

        rows = []
        for name in NAMES:
            amplitude = pr[name] / (P_CONSTANTS[name] * f[name] * one_plus_w[name])
            if name == "S0":
                phase = 0.0
            else:
                phase = v[name] + u[name] + w[name] + PHASE_P[name] + r[name] - PHASE_CYCLES[name]
            rows.append(
                {
                    "Name": name,
                    "Amplitude": float(amplitude),
                    "Phase": float(phase),
                    "Speed": CONSTITUENT_SPEEDS[name],
                    "PR": float(pr[name]),
                    "f": float(f[name]),
                    "u": float(u[name]),
                    "V": float(v[name]),
                    "w": float(w[name]),
                    "1+W": float(one_plus_w[name]),
                    "r": float(r[name]),
                }
            )

        by_name = {row["Name"]: row for row in rows}
        rows.append(
            {
                "Name": "K2",
                "Amplitude": by_name["S2"]["Amplitude"] * 0.27,
                "Phase": by_name["S2"]["Phase"],
                "Speed": CONSTITUENT_SPEEDS["K2"],
                "PR": np.nan,
                "f": float(f["K2"]),
                "u": float(u["K2"]),
                "V": float(v["K2"]),
                "w": np.nan,
                "1+W": np.nan,
                "r": np.nan,
            }
        )
        rows.append(
            {
                "Name": "P1",
                "Amplitude": by_name["K1"]["Amplitude"] * 0.33,
                "Phase": by_name["K1"]["Phase"],
                "Speed": CONSTITUENT_SPEEDS["P1"],
                "PR": np.nan,
                "f": float(f["P1"]),
                "u": float(u["P1"]),
                "V": float(v["P1"]),
                "w": np.nan,
                "1+W": np.nan,
                "r": np.nan,
            }
        )

        return pd.DataFrame(rows)

    def _compute_formzahl(self, constituents: pd.DataFrame) -> float:
        amps = constituents.set_index("Name")["Amplitude"]
        denominator = amps["M2"] + amps["S2"]
        if denominator == 0:
            return float("nan")
        return float((amps["K1"] + amps["O1"]) / denominator)

    def _classify_tide(self, formzahl: float) -> str:
        if np.isnan(formzahl):
            return "Tidak terklasifikasi"
        if formzahl <= 0.25:
            return "Harian Ganda"
        if formzahl <= 1.5:
            return "Campuran condong harian ganda"
        if formzahl <= 3.0:
            return "Campuran condong harian tunggal"
        return "Harian Tunggal"


def _linear(x: float, x0: float, x1: float, y0: float, y1: float) -> float:
    return ((x - x0) / (x1 - x0)) * (y1 - y0) + y0


def _positive_degrees(value: float) -> float:
    return float(value - np.floor(value / 360.0) * 360.0)
