from engine.processor import perform_analysis
from export.exporter import export_results
from PyQt6.QtWidgets import QMessageBox
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTabWidget,
    QTableWidget, QTableWidgetItem, QHeaderView, QFileDialog, QLabel
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
    def __init__(self, mode):
        super().__init__()
        self.mode = mode
        self.data = None
        self.predicted_df = None
        self.setWindowTitle(f"HydroTide Result - {self.mode}")
        self.resize(900, 700)

        main_layout = QVBoxLayout()
        self.setLayout(main_layout)

        # Tombol Import + label file
        self.btn_import = QPushButton("IMPORT DATA")
        self.btn_import.clicked.connect(self.import_data)
        self.file_label = QLabel("Belum ada file dipilih")
        main_layout.addWidget(self.btn_import)
        main_layout.addWidget(self.file_label)

        # Baris info: Formzahl + Tipe + RMSE
        info_layout = QHBoxLayout()
        self.lbl_formzahl = QLabel("Formzahl: -")
        self.lbl_type = QLabel("Tipe: -")
        self.lbl_rmse = QLabel("RMSE: -")
        for lbl in [self.lbl_formzahl, self.lbl_type, self.lbl_rmse]:
            lbl.setStyleSheet("font-weight: bold; padding: 4px 16px; "
                              "border: 1px solid #ccc; border-radius: 4px;")
            info_layout.addWidget(lbl)
        info_layout.addStretch()
        main_layout.addLayout(info_layout)

        # Tabs
        self.tabs = QTabWidget()

        # Tab Constants
        self.tab_const = QTableWidget()
        self.tab_const.setColumnCount(3)
        self.tab_const.setHorizontalHeaderLabels(["Name", "Amplitude (m)", "Phase (deg)"])
        self.tab_const.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tabs.addTab(self.tab_const, "Constants")

        # Tab Levels
        self.tab_levels = QTableWidget()
        self.tab_levels.setColumnCount(3)
        self.tab_levels.setHorizontalHeaderLabels(["Level", "Value (m)", "Jml. Kejadian"])
        self.tab_levels.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tabs.addTab(self.tab_levels, "Important Levels")

        # Tab Prediction
        self.plot_tab = QWidget()
        self.plot_layout = QVBoxLayout(self.plot_tab)
        self.figure = Figure(figsize=(8, 4))
        self.canvas = FigureCanvas(self.figure)
        self.btn_predict = QPushButton("Predict 1 Year")
        self.btn_predict.clicked.connect(self.on_predict_clicked)
        self.plot_layout.addWidget(self.canvas)
        self.plot_layout.addWidget(self.btn_predict)
        self.tabs.addTab(self.plot_tab, "Prediction")

        main_layout.addWidget(self.tabs)

        # Tombol Export
        self.btn_export = QPushButton("Export Results")
        self.btn_export.clicked.connect(self.export_data)
        main_layout.addWidget(self.btn_export)

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
            self, "Pilih Data Pasut", "", "Data Files (*.csv *.txt)"
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
            self.file_label.setText("Analisis Berhasil!")

        except Exception as e:
            QMessageBox.critical(self, "Gagal Analisis", f"Error pada engine:\n{str(e)}")
            self.file_label.setText("Gagal diproses.")

    def update_info(self, result):
        """Update label Formzahl, Tipe Pasut, dan RMSE."""
        formzahl = result.get('formzahl')
        tipe = result.get('type', '-')
        rmse = result.get('rmse')

        self.lbl_formzahl.setText(
            f"Formzahl: {formzahl:.4f}" if formzahl is not None else "Formzahl: -"
        )
        self.lbl_type.setText(f"Tipe: {tipe}")
        self.lbl_rmse.setText(
            f"RMSE: {rmse:.4f} m" if rmse is not None else "RMSE: -"
        )

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