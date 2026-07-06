import sys

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon
from app_info import APP_NAME, DEFAULT_BRAND, brand, resource_path
from gui.main_window import MainWindow

app = QApplication(sys.argv)
app.setApplicationName(APP_NAME)
app.setWindowIcon(QIcon(resource_path(brand(DEFAULT_BRAND)["icon"])))

window = MainWindow()
window.show()

sys.exit(app.exec())
