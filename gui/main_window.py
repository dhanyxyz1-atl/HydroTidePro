from PyQt6.QtWidgets import (
    QWidget,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QFrame,
)

from gui.result_window import ResultWindow


DEVELOPER_NAME = "dhanyxyz1-atl"


class MainWindow(QWidget):

    def __init__(self):
        super().__init__()

        self.theme = "light"
        self.setWindowTitle("HydroTide Pro")
        self.resize(780, 500)

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(28, 24, 28, 24)
        main_layout.setSpacing(14)
        self.setLayout(main_layout)

        header_layout = QHBoxLayout()

        header_text = QVBoxLayout()
        header_text.setSpacing(3)

        title = QLabel("HydroTide Pro")
        title.setObjectName("Title")

        subtitle = QLabel("Professional Harmonic Tide Analysis")
        subtitle.setObjectName("Subtitle")

        developer = QLabel(f"Developer: {DEVELOPER_NAME}")
        developer.setObjectName("Developer")

        header_text.addWidget(title)
        header_text.addWidget(subtitle)
        header_text.addWidget(developer)

        theme_layout = QHBoxLayout()
        theme_layout.setSpacing(8)

        self.btn_light = QPushButton("Light")
        self.btn_dark = QPushButton("Dark")
        self.btn_light.clicked.connect(lambda: self.set_theme("light"))
        self.btn_dark.clicked.connect(lambda: self.set_theme("dark"))

        theme_layout.addWidget(self.btn_light)
        theme_layout.addWidget(self.btn_dark)

        header_layout.addLayout(header_text)
        header_layout.addStretch()
        header_layout.addLayout(theme_layout)

        card = QFrame()
        card.setObjectName("Card")

        card_layout = QVBoxLayout()
        card_layout.setContentsMargins(22, 18, 22, 18)
        card_layout.setSpacing(10)

        section = QLabel("Input Data")
        section.setObjectName("SectionTitle")

        info = QLabel(
            "CSV / TXT: time,height\n"
            "Contoh: 01-07-2026 00:00,1.95\n\n"
            "Format waktu: DD-MM-YYYY HH:MM, YYYY-MM-DD HH:MM, atau MM-DD-YYYY HH:MM.\n"
            "Admiralty tetap bisa diproses untuk data kurang dari 29 hari. "
            "Data 29 hari adalah rekomendasi untuk mode referensi klasik."
        )
        info.setObjectName("InfoText")
        info.setWordWrap(True)

        card_layout.addWidget(section)
        card_layout.addWidget(info)
        card.setLayout(card_layout)

        method_layout = QHBoxLayout()
        method_layout.setSpacing(14)

        btn_adm = QPushButton("ADMIRALTY METHOD")
        btn_ls = QPushButton("LEAST SQUARE METHOD")
        btn_ls.setObjectName("Secondary")

        btn_adm.setMinimumHeight(52)
        btn_ls.setMinimumHeight(52)

        btn_adm.clicked.connect(self.open_admiralty)
        btn_ls.clicked.connect(self.open_lstsq)

        method_layout.addWidget(btn_adm)
        method_layout.addWidget(btn_ls)

        footer = QLabel("HydroTide Pro v1.0 | Admiralty & Least Square Tide Analysis")
        footer.setObjectName("Footer")

        main_layout.addLayout(header_layout)
        main_layout.addWidget(card)
        main_layout.addLayout(method_layout)
        main_layout.addStretch()
        main_layout.addWidget(footer)

        self.set_theme(self.theme)

    def set_theme(self, theme):
        self.theme = theme
        self.btn_light.setObjectName("ThemeActive" if theme == "light" else "ThemeButton")
        self.btn_dark.setObjectName("ThemeActive" if theme == "dark" else "ThemeButton")
        self.apply_theme()

    def apply_theme(self):
        self.setStyleSheet(self._theme_stylesheet())

    def _theme_stylesheet(self):
        if self.theme == "dark":
            return """
            QWidget {
                background-color: #0f172a;
                color: #e5e7eb;
                font-family: Segoe UI, Arial, sans-serif;
            }
            QLabel#Title {
                color: #f8fafc;
                font-size: 30px;
                font-weight: 800;
            }
            QLabel#Subtitle, QLabel#Developer, QLabel#Footer {
                color: #94a3b8;
                font-size: 13px;
            }
            QFrame#Card {
                background-color: #111827;
                border: 1px solid #334155;
                border-radius: 10px;
            }
            QLabel#SectionTitle {
                color: #f8fafc;
                font-size: 15px;
                font-weight: 800;
            }
            QLabel#InfoText {
                color: #cbd5e1;
                font-size: 12px;
                line-height: 140%;
            }
            QPushButton {
                background-color: #14b8a6;
                color: #042f2e;
                border: none;
                border-radius: 8px;
                padding: 12px 14px;
                font-size: 14px;
                font-weight: 800;
            }
            QPushButton:hover {
                background-color: #2dd4bf;
            }
            QPushButton#Secondary {
                background-color: #38bdf8;
                color: #082f49;
            }
            QPushButton#Secondary:hover {
                background-color: #7dd3fc;
            }
            QPushButton#ThemeButton {
                background-color: #1e293b;
                color: #e2e8f0;
                border: 1px solid #334155;
                padding: 9px 13px;
            }
            QPushButton#ThemeActive {
                background-color: #cffafe;
                color: #164e63;
                border: 1px solid #67e8f9;
                padding: 9px 13px;
            }
            """

        return """
        QWidget {
            background-color: #f5f7fb;
            color: #0f172a;
            font-family: Segoe UI, Arial, sans-serif;
        }
        QLabel#Title {
            color: #0f172a;
            font-size: 30px;
            font-weight: 800;
        }
        QLabel#Subtitle, QLabel#Developer, QLabel#Footer {
            color: #64748b;
            font-size: 13px;
        }
        QFrame#Card {
            background-color: #ffffff;
            border: 1px solid #dbe3ef;
            border-radius: 10px;
        }
        QLabel#SectionTitle {
            color: #0f172a;
            font-size: 15px;
            font-weight: 800;
        }
        QLabel#InfoText {
            color: #475569;
            font-size: 12px;
            line-height: 140%;
        }
        QPushButton {
            background-color: #0f766e;
            color: #ffffff;
            border: none;
            border-radius: 8px;
            padding: 12px 14px;
            font-size: 14px;
            font-weight: 800;
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
        QPushButton#ThemeButton {
            background-color: #e2e8f0;
            color: #0f172a;
            border: 1px solid #cbd5e1;
            padding: 9px 13px;
        }
        QPushButton#ThemeActive {
            background-color: #0f766e;
            color: #ffffff;
            border: 1px solid #0f766e;
            padding: 9px 13px;
        }
        """

    def open_admiralty(self):
        self.result_window = ResultWindow(
            mode="Admiralty",
            theme=self.theme,
        )
        self.result_window.show()

    def open_lstsq(self):
        self.result_window = ResultWindow(
            mode="Least Square (NumPy)",
            theme=self.theme,
        )
        self.result_window.show()
