from engine.processor import perform_analysis
from export.exporter import export_results
from PyQt6.QtWidgets import QMessageBox
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTabWidget,
    QTableWidget, QTableWidgetItem, QHeaderView, QFileDialog, QLabel,
    QFrame
)
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import pandas as pd
import os

LEVEL_LABELS = {
    "HWS":  "Highest Water Spring",
    "MHWS": "Mean High Water Spring",
    "MHWL": "Mean High Water Level",
    "MSL":  "Mean Sea Level",
    "MLWL": "Mean Low Water Level",
    "MLWS": "Mean Low Water Spring",
    "LWS":  "Lowest Water Spring",
}
LEVEL_ORDER = ["HWS", "MHWS", "MHWL", "MSL", "MLWL", "MLWS", "LWS"]


class ResultWindow(QWidget):
    def __init__(self, mode, theme="light"):
        super().__init__()
        self.mode = mode
        self.data = None
        self.predicted_df = None
        self.theme = theme if theme in {"light", "dark"} else "light"
        self.setWindowTitle(f"HydroTide Pro - {self.mode}")
        self.resize(980, 680)

        self.apply_theme()

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(24, 20, 24, 20)
        main_layout.setSpacing(12)
        self.setLayout(main_layout)

        header_layout = QHBoxLayout()
        header_text_layout = QVBoxLayout()
        header_text_layout.setSpacing(4)

        title = QLabel("HydroTide Pro")
        title.setObjectName("Title")

        self.file_label = QLabel("Belum ada file dipilih")
        self.file_label.setObjectName("FileLabel")

        header_text_layout.addWidget(title)
        header_text_layout.addWidget(self.file_label)

        mode_badge = QLabel(self.mode)
        mode_badge.setObjectName("ModeBadge")

        self.btn_import = QPushButton("Import Data")
        self.btn_import.clicked.connect(self.import_data)
        self.btn_import.setObjectName("SecondaryButton")

        header_layout.addLayout(header_text_layout)
        header_layout.addStretch()
        header_layout.addWidget(mode_badge)
        header_layout.addWidget(self.btn_import)
        main_layout.addLayout(header_layout)

        metric_layout = QHBoxLayout()
        metric_layout.setSpacing(10)
        self.card_formzahl, self.lbl_formzahl = self._make_metric_card("Formzahl", "-")
        self.card_type, self.lbl_type = self._make_metric_card("Tipe Pasut", "-")
        self.card_rmse, self.lbl_rmse = self._make_metric_card("RMSE", "-")
        metric_layout.addWidget(self.card_formzahl)
        metric_layout.addWidget(self.card_type)
        metric_layout.addWidget(self.card_rmse)
        main_layout.addLayout(metric_layout)

        meta_layout = QHBoxLayout()
        meta_layout.setSpacing(10)
        self.card_file, self.lbl_source_file = self._make_metric_card("File", "-")
        self.card_days, self.lbl_data_days = self._make_metric_card("Durasi Data", "-")
        self.card_method, self.lbl_method_card = self._make_metric_card("Metode", self.mode)
        meta_layout.addWidget(self.card_file)
        meta_layout.addWidget(self.card_days)
        meta_layout.addWidget(self.card_method)
        main_layout.addLayout(meta_layout)

        self.lbl_note = QLabel("")
        self.lbl_note.setObjectName("NoteLabel")
        self.lbl_note.setWordWrap(True)
        main_layout.addWidget(self.lbl_note)

        self.tabs = QTabWidget()

        self.tab_const = QTableWidget()
        self.tab_const.setColumnCount(3)
        self.tab_const.setHorizontalHeaderLabels(["Name", "Amplitude (m)", "Phase (deg)"])
        self.tab_const.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tab_const.setAlternatingRowColors(True)
        self.tab_const.verticalHeader().setVisible(False)
        self.tabs.addTab(self.tab_const, "Constants")

        self.tab_levels = QTableWidget()
        self.tab_levels.setColumnCount(3)
        self.tab_levels.setHorizontalHeaderLabels(["Level", "Value (m)", "Jml. Kejadian"])
        self.tab_levels.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tab_levels.setAlternatingRowColors(True)
        self.tab_levels.verticalHeader().setVisible(False)
        self.tabs.addTab(self.tab_levels, "Important Levels")

        self.plot_tab = QWidget()
        self.plot_layout = QVBoxLayout(self.plot_tab)
        self.plot_layout.setContentsMargins(12, 12, 12, 12)
        self.plot_layout.setSpacing(10)
        self.figure = Figure(figsize=(8, 4))
        self.canvas = FigureCanvas(self.figure)
        self.btn_predict = QPushButton("Predict 1 Year")
        self.btn_predict.setObjectName("SecondaryButton")
        self.btn_predict.clicked.connect(self.on_predict_clicked)
        self.plot_layout.addWidget(self.canvas)
        self.plot_layout.addWidget(self.btn_predict)
        self.tabs.addTab(self.plot_tab, "Prediction")

        main_layout.addWidget(self.tabs)

        footer_layout = QHBoxLayout()
        footer_layout.addStretch()
        self.btn_export = QPushButton("Export Results")
        self.btn_export.setObjectName("GhostButton")
        self.btn_export.clicked.connect(self.export_data)
        footer_layout.addWidget(self.btn_export)
        main_layout.addLayout(footer_layout)

    def _theme_stylesheet(self):
        if self.theme == "dark":
            return """
            QWidget {
                background-color: #0f172a;
                color: #e5e7eb;
                font-family: Segoe UI, Arial, sans-serif;
                font-size: 12px;
            }
            QLabel#Title { color: #f8fafc; font-size: 24px; font-weight: 800; }
            QLabel#ModeBadge {
                background-color: #164e63; color: #cffafe; border: 1px solid #155e75;
                border-radius: 8px; padding: 6px 10px; font-weight: 700;
            }
            QLabel#FileLabel, QLabel#NoteLabel, QLabel#MetricLabel { color: #94a3b8; }
            QFrame#MetricCard {
                background-color: #111827; border: 1px solid #334155; border-radius: 8px;
            }
            QLabel#MetricLabel { font-size: 11px; font-weight: 600; }
            QLabel#MetricValue { color: #f8fafc; font-size: 16px; font-weight: 800; }
            QPushButton {
                background-color: #14b8a6; color: #042f2e; border: none; border-radius: 8px;
                padding: 10px 14px; font-weight: 800;
            }
            QPushButton:hover { background-color: #2dd4bf; }
            QPushButton#SecondaryButton { background-color: #38bdf8; color: #082f49; }
            QPushButton#SecondaryButton:hover { background-color: #7dd3fc; }
            QPushButton#GhostButton { background-color: #1e293b; color: #e2e8f0; }
            QPushButton#GhostButton:hover { background-color: #334155; }
            QTabWidget::pane {
                background-color: #111827; border: 1px solid #334155; border-radius: 8px; top: -1px;
            }
            QTabBar::tab {
                background-color: #1e293b; color: #94a3b8; padding: 9px 16px;
                border-top-left-radius: 8px; border-top-right-radius: 8px;
                margin-right: 4px; font-weight: 700;
            }
            QTabBar::tab:selected {
                background-color: #111827; color: #f8fafc; border: 1px solid #334155;
                border-bottom-color: #111827;
            }
            QTableWidget {
                background-color: #111827; color: #e5e7eb; border: none;
                gridline-color: #334155; alternate-background-color: #0f172a;
                selection-background-color: #0f766e; selection-color: #ffffff;
            }
            QHeaderView::section {
                background-color: #1e293b; color: #e2e8f0; border: none;
                border-bottom: 1px solid #334155; padding: 8px; font-weight: 800;
            }
            """

        return """
            QWidget {
                background-color: #f5f7fb;
                color: #0f172a;
                font-family: Segoe UI, Arial, sans-serif;
                font-size: 12px;
            }
            QLabel#Title {
                color: #0f172a;
                font-size: 24px;
                font-weight: 800;
            }
            QLabel#ModeBadge {
                background-color: #e0f2fe;
                color: #075985;
                border: 1px solid #bae6fd;
                border-radius: 8px;
                padding: 6px 10px;
                font-weight: 700;
            }
            QLabel#FileLabel {
                color: #64748b;
                font-size: 12px;
            }
            QLabel#NoteLabel {
                color: #64748b;
                font-size: 11px;
                padding-top: 2px;
            }
            QFrame#MetricCard {
                background-color: #ffffff;
                border: 1px solid #dbe3ef;
                border-radius: 8px;
            }
            QLabel#MetricLabel {
                color: #64748b;
                font-size: 11px;
                font-weight: 600;
            }
            QLabel#MetricValue {
                color: #0f172a;
                font-size: 17px;
                font-weight: 800;
            }
            QPushButton {
                background-color: #0f766e;
                color: #ffffff;
                border: none;
                border-radius: 8px;
                padding: 10px 14px;
                font-weight: 700;
            }
            QPushButton:hover {
                background-color: #115e59;
            }
            QPushButton#SecondaryButton {
                background-color: #1d4ed8;
            }
            QPushButton#SecondaryButton:hover {
                background-color: #1e40af;
            }
            QPushButton#GhostButton {
                background-color: #e2e8f0;
                color: #0f172a;
            }
            QPushButton#GhostButton:hover {
                background-color: #cbd5e1;
            }
            QTabWidget::pane {
                background-color: #ffffff;
                border: 1px solid #dbe3ef;
                border-radius: 8px;
                top: -1px;
            }
            QTabBar::tab {
                background-color: #e2e8f0;
                color: #475569;
                padding: 9px 16px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                margin-right: 4px;
                font-weight: 700;
            }
            QTabBar::tab:selected {
                background-color: #ffffff;
                color: #0f172a;
                border: 1px solid #dbe3ef;
                border-bottom-color: #ffffff;
            }
            QTableWidget {
                background-color: #ffffff;
                border: none;
                gridline-color: #e2e8f0;
                alternate-background-color: #f8fafc;
                selection-background-color: #ccfbf1;
                selection-color: #0f172a;
            }
            QHeaderView::section {
                background-color: #f1f5f9;
                color: #334155;
                border: none;
                border-bottom: 1px solid #cbd5e1;
                padding: 8px;
                font-weight: 800;
            }
        """

    def apply_theme(self):
        self.setStyleSheet(self._theme_stylesheet())

    def _make_metric_card(self, label, value):
        card = QFrame()
        card.setObjectName("MetricCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(3)

        lbl = QLabel(label)
        lbl.setObjectName("MetricLabel")

        val = QLabel(value)
        val.setObjectName("MetricValue")

        layout.addWidget(lbl)
        layout.addWidget(val)
        return card, val

    def on_predict_clicked(self):
        if self.data is None:
            self.file_label.setText("Error: Analisis data belum dilakukan!")
            return

        try:
            reconstructor = self.data['reconstructor']

            # PENTING: pakai start_time dari data asli, bukan Timestamp.now()
            start_time = self.data.get('start_time', pd.Timestamp.now())
            time_range = pd.date_range(start=start_time, periods=8760, freq='h')

            predicted_heights = reconstructor.reconstruct(
                time_range, self.data.get('constituents')
            )

            self.predicted_df = pd.DataFrame({
                'time': time_range,
                'height': predicted_heights
            })

            self.figure.clear()
            ax = self.figure.add_subplot(111)
            ax.plot(time_range, predicted_heights, linewidth=0.8)
            ax.set_title("Prediksi Pasut 1 Tahun")
            ax.set_xlabel("Waktu")
            ax.set_ylabel("Tinggi Air (m)")
            self.figure.tight_layout()
            self.canvas.draw()
        except Exception as e:
            QMessageBox.critical(self, "Gagal Prediksi", f"Error pada reconstruct:\n{str(e)}")

    def import_data(self):
        filename, _ = QFileDialog.getOpenFileName(
            self, "Pilih Data Pasut", "", "Data Files (*.csv *.txt *.xlsx *.xls)"
        )
        if not filename:
            return

        try:
            self.file_label.setText(f"Memproses: {os.path.basename(filename)}...")

            if 'UTide' in self.mode:
                method_val = 'ols'
            elif 'NumPy' in self.mode:
                method_val = 'lstsq'
            else:
                method_val = 'admiralty'

            result = perform_analysis(filename, method=method_val)

            self.data = result
            self.predicted_df = None
            self.update_tables(result)
            self.update_info(result)      # tampilkan RMSE, Formzahl, Tipe

        except Exception as e:
            QMessageBox.critical(self, "Gagal Analisis", f"Error pada engine:\n{str(e)}")
            self.file_label.setText("Gagal diproses.")

    def update_info(self, result):
        """Update label Formzahl, Tipe Pasut, dan RMSE."""
        formzahl = result.get('formzahl')
        tipe = result.get('type', '-')
        rmse = result.get('rmse')

        self.lbl_formzahl.setText(
            f"{formzahl:.4f}" if formzahl is not None else "-"
        )
        self.lbl_type.setText(str(tipe))
        self.lbl_rmse.setText(
            f"{rmse:.4f} m" if rmse is not None else "-"
        )
        source_file = result.get("source_file", "-")
        data_days = result.get("data_days")
        data_points = result.get("data_points")
        method_label = result.get("method_label", self.mode)

        self.lbl_source_file.setText(str(source_file))
        self.lbl_data_days.setText(
            f"{data_days:.2f} hari ({data_points} data)"
            if data_days is not None and data_points is not None
            else "-"
        )
        self.lbl_method_card.setText(str(method_label))
        self.file_label.setText(
            f"{source_file} | {data_days:.2f} hari | {method_label}"
            if data_days is not None
            else str(source_file)
        )

        note = result.get("analysis_note", "")
        self.lbl_note.setText(note)

    def update_tables(self, result):
        # Tab Constants
        df_const = result.get('constituents')
        if df_const is None:
            self.tab_const.setRowCount(0)
        else:
            self.tab_const.setRowCount(len(df_const))
            for i, row in df_const.reset_index(drop=True).iterrows():
                self.tab_const.setItem(i, 0, QTableWidgetItem(str(row['Name'])))
                self.tab_const.setItem(i, 1, QTableWidgetItem(f"{row.get('Amplitude', 0):.4f}"))
                self.tab_const.setItem(i, 2, QTableWidgetItem(f"{row.get('Phase', 0):.2f}"))

        # Tab Important Levels
        levels = result.get('levels', {})
        self.tab_levels.setRowCount(len(LEVEL_ORDER))
        for i, key in enumerate(LEVEL_ORDER):
            label = f"{LEVEL_LABELS.get(key, key)} ({key})"
            if key not in levels:
                self.tab_levels.setItem(i, 0, QTableWidgetItem(label))
                self.tab_levels.setItem(i, 1, QTableWidgetItem("N/A"))
                self.tab_levels.setItem(i, 2, QTableWidgetItem("0"))
                continue
            value, count = levels[key]
            self.tab_levels.setItem(i, 0, QTableWidgetItem(label))
            self.tab_levels.setItem(i, 1, QTableWidgetItem(f"{value:.3f}"))
            self.tab_levels.setItem(i, 2, QTableWidgetItem(str(count)))

    def export_data(self):
        if self.data is None:
            QMessageBox.warning(self, "Belum Ada Data",
                                "Lakukan analisis terlebih dahulu sebelum export.")
            return

        filename, _ = QFileDialog.getSaveFileName(
            self, "Export Hasil", "", "Excel File (*.xlsx);;CSV File (*.csv)"
        )
        if not filename:
            return

        try:
            export_results(self.data, filename, predicted_df=self.predicted_df)
            QMessageBox.information(self, "Export Berhasil", f"Hasil disimpan ke:\n{filename}")
        except Exception as e:
            QMessageBox.critical(self, "Gagal Export", f"Error saat export:\n{str(e)}")
