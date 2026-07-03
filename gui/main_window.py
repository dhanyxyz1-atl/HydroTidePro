from PyQt6.QtWidgets import (
    QWidget,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QFrame
)
from PyQt6.QtCore import Qt

from gui.result_window import ResultWindow


class MainWindow(QWidget):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("HydroTide Pro")
        self.resize(760, 480)

        self.setStyleSheet("""
            QWidget {
                background-color: #f4f7fb;
                font-family: Segoe UI;
                color: #1f2937;
            }

            QLabel#Title {
                font-size: 30px;
                font-weight: bold;
                color: #0f172a;
            }

            QLabel#Subtitle {
                font-size: 13px;
                color: #64748b;
            }

            QFrame#Card {
                background-color: white;
                border-radius: 14px;
                border: 1px solid #dbe3ef;
            }

            QLabel#SectionTitle {
                font-size: 15px;
                font-weight: bold;
                color: #0f172a;
            }

            QLabel#InfoText {
                font-size: 12px;
                color: #475569;
                line-height: 140%;
            }

            QPushButton {
                background-color: #0f766e;
                color: white;
                border: none;
                border-radius: 10px;
                padding: 14px;
                font-size: 14px;
                font-weight: bold;
            }

            QPushButton:hover {
                background-color: #115e59;
            }

            QPushButton#Secondary {
                background-color: #1d4ed8;
            }

            QPushButton#Secondary:hover {
                background-color: #1e40af;
            }
        """)

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(32, 28, 32, 28)
        main_layout.setSpacing(18)

        title = QLabel("HydroTide Pro 🌊")
        title.setObjectName("Title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        subtitle = QLabel("Professional Harmonic Tide Analysis")
        subtitle.setObjectName("Subtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)

        card = QFrame()
        card.setObjectName("Card")

        card_layout = QVBoxLayout()
        card_layout.setContentsMargins(24, 20, 24, 20)
        card_layout.setSpacing(14)

        section = QLabel("Supported Data Format")
        section.setObjectName("SectionTitle")

        info = QLabel(
            "Input CSV / TXT:\n"
            "time,height\n"
            "01-07-2026 00:00,1.95\n"
            "01-07-2026 01:00,1.88\n\n"
            "Supported time format:\n"
            "DD-MM-YYYY HH:MM | YYYY-MM-DD HH:MM | MM-DD-YYYY HH:MM\n\n"
            "Admiralty Method requires minimum 29 days of hourly tide data."
        )
        info.setObjectName("InfoText")
        info.setWordWrap(True)

        card_layout.addWidget(section)
        card_layout.addWidget(info)
        card.setLayout(card_layout)

        button_layout = QHBoxLayout()
        button_layout.setSpacing(16)

        btn_adm = QPushButton("ADMIRALTY METHOD")
        btn_ls = QPushButton("LEAST SQUARE METHOD")
        btn_ls.setObjectName("Secondary")

        btn_adm.setMinimumHeight(56)
        btn_ls.setMinimumHeight(56)

        btn_adm.clicked.connect(self.open_admiralty)
        btn_ls.clicked.connect(self.open_lstsq)

        button_layout.addWidget(btn_adm)
        button_layout.addWidget(btn_ls)

        footer = QLabel("HydroTide Pro v1.0  |  Admiralty & Least Square Tide Analysis")
        footer.setObjectName("Subtitle")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)

        main_layout.addWidget(title)
        main_layout.addWidget(subtitle)
        main_layout.addWidget(card)
        main_layout.addLayout(button_layout)
        main_layout.addStretch()
        main_layout.addWidget(footer)

        self.setLayout(main_layout)

    def open_admiralty(self):
        self.result_window = ResultWindow(mode="Admiralty")
        self.result_window.show()

    def open_lstsq(self):
        self.result_window = ResultWindow(mode="Least Square (NumPy)")
        self.result_window.show()