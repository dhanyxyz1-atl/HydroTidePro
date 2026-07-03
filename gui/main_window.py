from PyQt6.QtWidgets import QWidget, QLabel, QPushButton, QVBoxLayout
from gui.result_window import ResultWindow


class MainWindow(QWidget):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("HydroTide Professional")
        self.resize(500, 400)

        layout = QVBoxLayout()

        title = QLabel("HYDROTIDE PROFESSIONAL")

        btn_ls = QPushButton("HARMONIC LEAST SQUARE (UTide)")
        btn_lstsq = QPushButton("HARMONIC LEAST SQUARE (NumPy)")
        btn_adm = QPushButton("HARMONIC ADMIRALTY")

        btn_ls.clicked.connect(self.open_least_square)
        btn_lstsq.clicked.connect(self.open_lstsq)
        btn_adm.clicked.connect(self.open_admiralty)

        layout.addWidget(title)
        layout.addWidget(btn_ls)
        layout.addWidget(btn_lstsq)
        layout.addWidget(btn_adm)

        self.setLayout(layout)

    def open_least_square(self):
        self.result_window = ResultWindow(mode='Least Square (UTide)')
        self.result_window.show()

    def open_lstsq(self):
        self.result_window = ResultWindow(mode='Least Square (NumPy)')
        self.result_window.show()

    def open_admiralty(self):
        self.result_window = ResultWindow(mode='Admiralty')
        self.result_window.show()
