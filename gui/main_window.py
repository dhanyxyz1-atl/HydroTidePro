from PyQt6.QtWidgets import QWidget, QLabel, QPushButton, QVBoxLayout
from gui.result_window import ResultWindow


class MainWindow(QWidget):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("HydroTide Professional")
        self.resize(500, 300)

        layout = QVBoxLayout()

        title = QLabel("HYDROTIDE PROFESSIONAL")

        btn_ls = QPushButton("HARMONIC LEAST SQUARE")
        btn_adm = QPushButton("HARMONIC ADMIRALTY")

        btn_ls.clicked.connect(self.open_least_square)
        btn_adm.clicked.connect(self.open_admiralty)

        layout.addWidget(title)
        layout.addWidget(btn_ls)
        layout.addWidget(btn_adm)

        self.setLayout(layout)

    def open_least_square(self):
        self.result_window = ResultWindow(mode='Least Square')
        self.result_window.show()

    def open_admiralty(self):
        self.result_window = ResultWindow(mode='Admiralty')
        self.result_window.show()