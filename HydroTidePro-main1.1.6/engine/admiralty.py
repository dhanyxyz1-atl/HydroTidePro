import numpy as np
import pandas as pd
from engine.admiralty_excel import AdmiraltyEngine as ExcelReferenceAdmiraltyEngine
from engine.levels import compute_important_levels


class AdmiraltyEngine:
    CONSTITUENTS = {
        "M2": 28.9841042,
        "S2": 30.0000000,
        "N2": 28.4397295,
        "K1": 15.0410686,
        "O1": 13.9429539,
        "M4": 57.9682084,
        "MS4": 58.9841042,
        "K2": 30.0821373,
        "P1": 14.9589333,
    }

    DEFAULT_CONSTITUENTS = ["M2", "S2", "K1", "O1", "N2", "M4", "MS4", "K2", "P1"]
    RECOMMENDED_HOURS = 29 * 24

    def __init__(self, constituents=None, use_precision_calibration=True):
        self.requested_constituents = constituents or self.DEFAULT_CONSTITUENTS
        self.constituent_names = list(self.requested_constituents)
        self.coef = None
        self.start_time = None
        self.analysis_note = None
        self.use_precision_calibration = use_precision_calibration

    def run_analysis(self, df):
        df = (
            df.copy()
            .sort_values("time")
            .drop_duplicates(subset="time")
            .reset_index(drop=True)
        )
        df["time"] = pd.to_datetime(df["time"])
        df["height"] = pd.to_numeric(df["height"], errors="coerce")
        df = df.dropna(subset=["time", "height"]).reset_index(drop=True)

        if len(df) < 3:
            raise ValueError("Data is too short. Admiralty requires at least 3 data points.")

        self.start_time = df["time"].iloc[0]
        if self._has_excel_reference_window(df):
            return self._run_excel_reference(df)

        self.constituent_names = self._select_constituents(len(df))
        self.analysis_note = self._build_analysis_note(len(df))

        t_hours = self._time_to_hours(df["time"])
        heights = df["height"].to_numpy(dtype=float)

        matrix = self._build_design_matrix(t_hours)
        self.coef, _, _, _ = np.linalg.lstsq(matrix, heights, rcond=None)
        constituents = self._extract_constituents(self.coef)
        constituents, calibration = self._maybe_calibrate_constituents(
            df["time"], heights, constituents
        )

        f = self._compute_formzahl(constituents)
        tide_type = self._classify_tide(f)

        year_hours = pd.date_range(start=self.start_time, periods=8760, freq="h")
        predicted_curve = self.reconstruct(year_hours, constituents)
        levels = compute_important_levels(year_hours, predicted_curve)
        predicted_obs = self.reconstruct(df["time"], constituents)
        metrics = self._fit_metrics(heights, predicted_obs)
        self.analysis_note = self._append_calibration_note(self.analysis_note, calibration)

        return {
            "constituents": constituents,
            "formzahl": f,
            "type": tide_type,
            "levels": levels,
            "rmse": metrics["rmse"],
            "r2": metrics["r2"],
            "rmse_percent_range": metrics["rmse_percent_range"],
            "quality": metrics["quality"],
            "start_time": self.start_time,
            "analysis_note": self.analysis_note,
            "precision_calibrated": calibration["applied"],
            "reconstructor": self
        }

    def reconstruct(self, time_array, constituents):
        time_array = pd.to_datetime(pd.Series(time_array).reset_index(drop=True))
        if self.start_time is None:
            self.start_time = time_array.iloc[0]
        t = (time_array - self.start_time).dt.total_seconds().values / 3600.0

        result = np.zeros(len(time_array), dtype=float)
        for _, row in constituents.iterrows():
            name = row["Name"]
            amplitude = float(row["Amplitude"])
            phase = float(row["Phase"])
            speed = float(row["Speed"])

            if name in {"Z0", "S0"} or speed == 0:
                result += amplitude
            else:
                result += amplitude * np.cos(
                    np.radians(speed * t) - np.radians(phase)
                )

        return result

    def _time_to_hours(self, time_array):
        time_array = pd.to_datetime(pd.Series(time_array).reset_index(drop=True))
        return (time_array - self.start_time).dt.total_seconds().values / 3600.0

    def _build_design_matrix(self, t_hours):
        columns = [np.ones(len(t_hours))]
        for name in self.constituent_names:
            speed_rad = np.radians(self.CONSTITUENTS[name])
            columns.append(np.cos(speed_rad * t_hours))
            columns.append(np.sin(speed_rad * t_hours))
        return np.column_stack(columns)

    def _select_constituents(self, n_points):
        max_constituents = max(1, (n_points - 1) // 2)
        return list(self.requested_constituents[:max_constituents])

    def _build_analysis_note(self, n_points):
        available_hours = n_points
        if available_hours >= self.RECOMMENDED_HOURS:
            return "Admiralty was processed with the recommended 29-day minimum or longer."

        available_days = available_hours / 24.0
        used = ", ".join(self.constituent_names)
        return (
            f"Available data: {available_days:.2f} days. "
            "A 29-day record is the recommended minimum for classical Admiralty; "
            f"the analysis was still processed with adaptive constituents: {used}."
        )

    def _extract_constituents(self, coef):
        rows = [{
            "Name": "Z0",
            "Amplitude": float(coef[0]),
            "Phase": 0.0,
            "Speed": 0.0,
        }]

        idx = 1
        for name in self.constituent_names:
            a = coef[idx]
            b = coef[idx + 1]
            idx += 2

            amplitude = float(np.hypot(a, b))
            phase = float(np.degrees(np.arctan2(b, a)))
            if phase < 0:
                phase += 360.0

            rows.append({
                "Name": name,
                "Amplitude": amplitude,
                "Phase": phase,
                "Speed": self.CONSTITUENTS[name],
            })

        return pd.DataFrame(rows)

    def _has_excel_reference_window(self, df):
        if len(df) < self.RECOMMENDED_HOURS:
            return False

        start = df["time"].iloc[0].floor("D")
        if df["time"].iloc[0] != start:
            return False

        expected = pd.date_range(start=start, periods=self.RECOMMENDED_HOURS, freq="h")
        available = set(pd.to_datetime(df["time"].iloc[: self.RECOMMENDED_HOURS]))
        return all(ts in available for ts in expected)

    def _run_excel_reference(self, df):
        scale = self._excel_height_scale(df["height"])
        excel_df = df.copy()
        excel_df["height"] = excel_df["height"] * scale

        backend = ExcelReferenceAdmiraltyEngine(days=29)
        backend_result = backend.run_analysis(excel_df)
        reference_constituents = backend_result["constituents"].copy()
        reference_constituents["Amplitude"] = reference_constituents["Amplitude"] / scale

        reference_time = df["time"].iloc[: self.RECOMMENDED_HOURS]
        reference_height = df["height"].iloc[: self.RECOMMENDED_HOURS].to_numpy(dtype=float)
        reference_prediction = self.reconstruct(reference_time, reference_constituents)
        reference_metrics = self._fit_metrics(reference_height, reference_prediction)

        heights = df["height"].to_numpy(dtype=float)
        constituents, calibration = self._maybe_calibrate_constituents(
            df["time"], heights, reference_constituents
        )

        year_hours = pd.date_range(start=self.start_time, periods=8760, freq="h")
        predicted_curve = self.reconstruct(year_hours, constituents)
        levels = compute_important_levels(year_hours, predicted_curve)

        predicted_obs = self.reconstruct(df["time"], constituents)
        metrics = self._fit_metrics(heights, predicted_obs)
        formzahl = self._compute_formzahl(constituents)

        extra_note = ""
        if len(df) > self.RECOMMENDED_HOURS:
            extra_note = (
                f" Input has {len(df)} rows; the Excel-reference backend uses the first "
                "29 days, then precision calibration uses the full available record."
            )

        self.analysis_note = (
            "Admiralty was processed with the Excel-reference backend "
            "(Schema I-IV, Tables V-VIII, and f, u, V, w, 1+W corrections)."
            + extra_note
        )
        self.analysis_note = self._append_calibration_note(self.analysis_note, calibration)

        return {
            "constituents": constituents,
            "reference_constituents": reference_constituents,
            "formzahl": formzahl,
            "type": self._classify_tide(formzahl),
            "levels": levels,
            "rmse": metrics["rmse"],
            "r2": metrics["r2"],
            "rmse_percent_range": metrics["rmse_percent_range"],
            "quality": metrics["quality"],
            "reference_rmse": reference_metrics["rmse"],
            "reference_r2": reference_metrics["r2"],
            "start_time": self.start_time,
            "analysis_note": self.analysis_note,
            "used_data_points": self.RECOMMENDED_HOURS,
            "used_data_days": 29.0,
            "precision_calibrated": calibration["applied"],
            "reconstructor": self
        }

    def _excel_height_scale(self, heights):
        max_abs = float(np.nanmax(np.abs(pd.to_numeric(heights, errors="coerce"))))
        return 100.0 if max_abs < 20.0 else 1.0

    def _amplitude(self, constituents, name):
        match = constituents.loc[constituents["Name"] == name, "Amplitude"]
        return float(match.iloc[0]) if not match.empty else 0.0

    def _compute_formzahl(self, constituents):
        k1 = self._amplitude(constituents, "K1")
        o1 = self._amplitude(constituents, "O1")
        m2 = self._amplitude(constituents, "M2")
        s2 = self._amplitude(constituents, "S2")
        denominator = m2 + s2
        return (k1 + o1) / denominator if denominator else 0.0

    def _classify_tide(self, formzahl):
        if formzahl < 0.25:
            return "Semi-Diurnal"
        if formzahl < 1.5:
            return "Mixed, mainly semi-diurnal"
        if formzahl < 3.0:
            return "Mixed, mainly diurnal"
        return "Diurnal"

    def _maybe_calibrate_constituents(self, time_array, heights, constituents):
        calibration = {
            "applied": False,
            "before_rmse": None,
            "after_rmse": None,
        }
        if not self.use_precision_calibration:
            return constituents, calibration

        heights = np.asarray(heights, dtype=float)
        if len(heights) < 3:
            return constituents, calibration

        base_prediction = self.reconstruct(time_array, constituents)
        base_metrics = self._fit_metrics(heights, base_prediction)
        calibration["before_rmse"] = base_metrics["rmse"]

        harmonic_rows = constituents[
            (constituents["Speed"].astype(float) != 0.0)
            & (~constituents["Name"].isin(["S0", "Z0"]))
        ].copy()
        if harmonic_rows.empty:
            return constituents, calibration

        t_hours = self._time_to_hours(time_array)
        matrix = self._calibration_design_matrix(t_hours, harmonic_rows)
        coef, _, _, _ = np.linalg.lstsq(matrix, heights, rcond=None)
        calibrated = self._constituents_from_calibration(coef, harmonic_rows, constituents)
        calibrated_prediction = self.reconstruct(time_array, calibrated)
        calibrated_metrics = self._fit_metrics(heights, calibrated_prediction)
        calibration["after_rmse"] = calibrated_metrics["rmse"]

        if calibrated_metrics["rmse"] <= base_metrics["rmse"]:
            calibration["applied"] = True
            return calibrated, calibration

        return constituents, calibration

    def _calibration_design_matrix(self, t_hours, harmonic_rows):
        columns = [np.ones(len(t_hours))]
        for _, row in harmonic_rows.iterrows():
            speed_rad = np.radians(float(row["Speed"]))
            columns.append(np.cos(speed_rad * t_hours))
            columns.append(np.sin(speed_rad * t_hours))
        return np.column_stack(columns)

    def _constituents_from_calibration(self, coef, harmonic_rows, original_constituents):
        zero_name = "S0" if "S0" in set(original_constituents["Name"]) else "Z0"
        rows = [{
            "Name": zero_name,
            "Amplitude": float(coef[0]),
            "Phase": 0.0,
            "Speed": 0.0,
        }]

        idx = 1
        for _, source in harmonic_rows.iterrows():
            a = coef[idx]
            b = coef[idx + 1]
            idx += 2
            amplitude = float(np.hypot(a, b))
            phase = float(np.degrees(np.arctan2(b, a)))
            if phase < 0:
                phase += 360.0
            rows.append({
                "Name": source["Name"],
                "Amplitude": amplitude,
                "Phase": phase,
                "Speed": float(source["Speed"]),
            })

        return pd.DataFrame(rows)

    def _fit_metrics(self, observed, predicted):
        observed = np.asarray(observed, dtype=float)
        predicted = np.asarray(predicted, dtype=float)
        rmse = float(np.sqrt(np.mean((observed - predicted) ** 2)))
        ss_res = float(np.sum((observed - predicted) ** 2))
        ss_tot = float(np.sum((observed - np.mean(observed)) ** 2))
        r2 = float(1.0 - ss_res / ss_tot) if ss_tot else 0.0
        data_range = float(np.max(observed) - np.min(observed))
        rmse_percent_range = float((rmse / data_range) * 100.0) if data_range else 0.0
        return {
            "rmse": rmse,
            "r2": r2,
            "rmse_percent_range": rmse_percent_range,
            "quality": self._classify_quality(r2, rmse_percent_range),
        }

    def _classify_quality(self, r2, rmse_percent_range):
        if r2 >= 0.95 and rmse_percent_range < 5.0:
            return "Sangat baik"
        if r2 >= 0.90 and rmse_percent_range < 10.0:
            return "Baik"
        if r2 >= 0.75 and rmse_percent_range < 20.0:
            return "Cukup baik"
        return "Perlu evaluasi"

    def _append_calibration_note(self, note, calibration):
        if not calibration["applied"]:
            return note

        before = calibration["before_rmse"]
        after = calibration["after_rmse"]
        return (
            f"{note} Precision calibration was applied to the Admiralty harmonic "
            f"constituents to improve observed-data fit (RMSE {before:.4f} -> {after:.4f})."
        )
