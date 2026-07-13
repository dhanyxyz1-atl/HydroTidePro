import os

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QFileDialog,
    QMessageBox, QFrame
)
from PyQt6.QtGui import QIcon
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from app_info import APP_NAME, DEFAULT_BRAND, brand, resource_path
from engine.processor import perform_analysis_from_df
from engine.tide_preprocess import (
    invert_and_shift_tide,
    load_embedded_reference_series,
    load_reference_series,
    load_tide_series,
)
from export.exporter import export_preprocess_result
from gui.result_window import ResultWindow


class PreprocessWindow(QWidget):
    def __init__(self, theme="light"):
        super().__init__()
        self.theme = theme if theme in {"light", "dark"} else "light"
        self.source_path = None
        self.reference_path = None
        self.source_df = None
        self.reference_df = None
        self.processed = None
        self.brand = brand(DEFAULT_BRAND)

        self.setWindowTitle(f"{APP_NAME} - Invert & Shift Tide")
        self.setWindowIcon(QIcon(resource_path(self.brand["icon"])))
        self.resize(1020, 700)
        self.apply_theme()

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(12)

        header = QHBoxLayout()
        title_group = QVBoxLayout()
        title = QLabel("Invert & Shift Tide")
        title.setObjectName("Title")
        self.subtitle = QLabel("Load source tide, optionally align it to a reference datum, then continue to analysis.")
        self.subtitle.setObjectName("FileLabel")
        title_group.addWidget(title)
        title_group.addWidget(self.subtitle)

        self.btn_source = QPushButton("Load Source Tide")
        self.btn_source.setObjectName("SecondaryButton")
        self.btn_reference = QPushButton("Load Optional Reference")
        self.btn_reference.setObjectName("GhostButton")
        self.btn_process = QPushButton("Apply Invert & Shift")

        self.btn_source.clicked.connect(self.load_source)
        self.btn_reference.clicked.connect(self.load_reference)
        self.btn_process.clicked.connect(self.process_data)

        header.addLayout(title_group)
        header.addStretch()
        header.addWidget(self.btn_source)
        header.addWidget(self.btn_reference)
        header.addWidget(self.btn_process)
        root.addLayout(header)

        metrics = QHBoxLayout()
        self.card_source, self.lbl_source = self._make_card("Source File", "-")
        self.card_ref, self.lbl_reference = self._make_card("Reference File", "Optional")
        self.card_stats, self.lbl_stats = self._make_card("Processing", "-")
        metrics.addWidget(self.card_source)
        metrics.addWidget(self.card_ref)
        metrics.addWidget(self.card_stats)
        root.addLayout(metrics)

        self.figure = Figure(figsize=(8, 4))
        self.canvas = FigureCanvas(self.figure)
        root.addWidget(self.canvas)

        next_row = QHBoxLayout()
        self.note = QLabel("Choose a source file to begin.")
        self.note.setObjectName("NoteLabel")
        self.note.setWordWrap(True)
        self.btn_admiralty = QPushButton("Continue with Admiralty")
        self.btn_lstsq = QPushButton("Continue with Least Square")
        self.btn_export = QPushButton("Export Processed Tide")
        self.btn_export.setObjectName("GhostButton")
        self.btn_lstsq.setObjectName("SecondaryButton")
        self.btn_admiralty.clicked.connect(lambda: self.continue_analysis("admiralty"))
        self.btn_lstsq.clicked.connect(lambda: self.continue_analysis("lstsq"))
        self.btn_export.clicked.connect(self.export_processed)
        self.btn_admiralty.setEnabled(False)
        self.btn_lstsq.setEnabled(False)
        self.btn_export.setEnabled(False)

        next_row.addWidget(self.note)
        next_row.addStretch()
        next_row.addWidget(self.btn_export)
        next_row.addWidget(self.btn_admiralty)
        next_row.addWidget(self.btn_lstsq)
        root.addLayout(next_row)

    def load_source(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Load Source Tide",
            "",
            "Data Files (*.csv *.txt *.xlsx *.xls *.xlsm)",
        )
        if not path:
            return
        try:
            self.source_path = path
            self.source_df = load_tide_series(path, preferred="source")
            self.reference_df = load_embedded_reference_series(path)
            self.reference_path = path if self.reference_df is not None else None

            self.lbl_source.setText(f"{os.path.basename(path)} | {len(self.source_df)} rows")
            if self.reference_df is not None:
                self.lbl_reference.setText(f"Embedded reference | {len(self.reference_df)} rows")
            else:
                self.lbl_reference.setText("Optional")
            self.note.setText("Source loaded. Apply invert & shift, or load a separate reference first.")
            self.plot_preview()
        except Exception as exc:
            QMessageBox.critical(self, "Load Failed", str(exc))

    def load_reference(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Load Optional Reference Tide",
            "",
            "Data Files (*.csv *.txt *.xlsx *.xls *.xlsm)",
        )
        if not path:
            return
        try:
            self.reference_path = path
            self.reference_df = load_reference_series(path)
            self.lbl_reference.setText(f"{os.path.basename(path)} | {len(self.reference_df)} rows")
            self.note.setText("Reference loaded. Apply invert & shift to generate analysis-ready tide.")
            self.plot_preview()
        except Exception as exc:
            QMessageBox.critical(self, "Reference Load Failed", str(exc))

    def process_data(self):
        if self.source_df is None:
            QMessageBox.warning(self, "No Source Data", "Load source tide data first.")
            return
        try:
            self.processed = invert_and_shift_tide(self.source_df, self.reference_df)
            source_stats = self.processed["source_stats"]
            ref_stats = self.processed["reference_stats"]
            stats = (
                f"Source MSL {source_stats['msl']:.3f} m | "
                f"Output rows {len(self.processed['analysis'])}"
            )
            if ref_stats:
                stats += f" | Reference MSL {ref_stats['msl']:.3f} m"
            self.lbl_stats.setText(stats)
            self.note.setText(self.processed["note"])
            self.btn_admiralty.setEnabled(True)
            self.btn_lstsq.setEnabled(True)
            self.btn_export.setEnabled(True)
            self.plot_preview()
        except Exception as exc:
            QMessageBox.critical(self, "Processing Failed", str(exc))

    def export_processed(self):
        if self.processed is None:
            QMessageBox.warning(self, "No Processed Data", "Apply invert & shift before exporting.")
            return

        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Invert & Shift Result",
            "",
            "Excel File (*.xlsx)",
        )
        if not path:
            return
        if not path.lower().endswith(".xlsx"):
            path += ".xlsx"

        try:
            export_preprocess_result(self.processed, path)
            QMessageBox.information(self, "Export Complete", f"Processed tide saved to:\n{path}")
        except Exception as exc:
            QMessageBox.critical(self, "Export Failed", str(exc))

    def continue_analysis(self, method):
        if self.processed is None:
            QMessageBox.warning(self, "No Processed Data", "Apply invert & shift before continuing.")
            return
        try:
            label = "Admiralty" if method == "admiralty" else "Least Square (NumPy)"
            source = os.path.basename(self.source_path) if self.source_path else "Processed tide"
            result = perform_analysis_from_df(
                self.processed["analysis"],
                method=method,
                source_file=f"InvertShift_{source}",
                source_path=self.source_path,
            )
            result["preprocess_note"] = self.processed["note"]
            self.result_window = ResultWindow(
                mode=label,
                theme=self.theme,
                initial_result=result,
            )
            self.result_window.show()
        except Exception as exc:
            QMessageBox.critical(self, "Analysis Failed", str(exc))

    def plot_preview(self):
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        if self.source_df is not None:
            ax.plot(self.source_df["time"], self.source_df["height"], label="Raw source", linewidth=0.8)
        if self.reference_df is not None:
            ax.plot(self.reference_df["time"], self.reference_df["height"], label="Reference", linewidth=0.8)
        if self.processed is not None:
            df = self.processed["processed"]
            ax.plot(df["time"], df["inverted_height"], label="Inverted", linewidth=0.8)
            ax.plot(df["time"], df["shifted_height"], label="Shifted output", linewidth=1.2)

        ax.set_title("Tide Invert & Shift Preview")
        ax.set_xlabel("Time")
        ax.set_ylabel("Water Level (m)")
        ax.grid(True, alpha=0.25)
        ax.legend(loc="best")
        self.figure.tight_layout()
        self.canvas.draw()

    def _make_card(self, label, value):
        card = QFrame()
        card.setObjectName("MetricCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(3)
        title = QLabel(label)
        title.setObjectName("MetricLabel")
        metric = QLabel(value)
        metric.setObjectName("MetricValue")
        metric.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(metric)
        return card, metric

    def apply_theme(self):
        self.setStyleSheet(self._theme_stylesheet())

    def _theme_stylesheet(self):
        font_family = self.brand["font"]
        if self.theme == "dark":
            css = """
            QWidget { background-color: #0f172a; color: #e5e7eb; font-family: __FONT__; font-size: 12px; }
            QLabel#Title { color: #f8fafc; font-size: 24px; font-weight: 800; }
            QLabel#FileLabel, QLabel#NoteLabel, QLabel#MetricLabel { color: #94a3b8; }
            QFrame#MetricCard { background-color: #111827; border: 1px solid #334155; border-radius: 8px; }
            QLabel#MetricLabel { font-size: 11px; font-weight: 600; }
            QLabel#MetricValue { color: #f8fafc; font-size: 14px; font-weight: 800; }
            QPushButton { background-color: #0e7490; color: #ecfeff; border: none; border-radius: 8px; padding: 10px 14px; font-weight: 800; }
            QPushButton:hover { background-color: #0891b2; }
            QPushButton:disabled { background-color: #334155; color: #64748b; }
            QPushButton#SecondaryButton { background-color: #1d4ed8; color: #eff6ff; }
            QPushButton#GhostButton { background-color: #1e293b; color: #e2e8f0; }
            """
        else:
            css = """
            QWidget { background-color: #f5f7fb; color: #0f172a; font-family: __FONT__; font-size: 12px; }
            QLabel#Title { color: #0f172a; font-size: 24px; font-weight: 800; }
            QLabel#FileLabel, QLabel#NoteLabel, QLabel#MetricLabel { color: #64748b; }
            QFrame#MetricCard { background-color: #ffffff; border: 1px solid #dbe3ef; border-radius: 8px; }
            QLabel#MetricLabel { font-size: 11px; font-weight: 600; }
            QLabel#MetricValue { color: #0f172a; font-size: 14px; font-weight: 800; }
            QPushButton { background-color: #0e7490; color: #ffffff; border: none; border-radius: 8px; padding: 10px 14px; font-weight: 800; }
            QPushButton:hover { background-color: #155e75; }
            QPushButton:disabled { background-color: #cbd5e1; color: #64748b; }
            QPushButton#SecondaryButton { background-color: #1d4ed8; }
            QPushButton#GhostButton { background-color: #e2e8f0; color: #0f172a; }
            """
        return css.replace("__FONT__", font_family)
