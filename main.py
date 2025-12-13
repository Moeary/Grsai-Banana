import sys
import os
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
from PySide6.QtCore import Qt

# Enable High DPI support
# PySide6 handles High DPI automatically in most cases, but explicit attributes can still be set if needed.
# QApplication.setAttribute(Qt.AA_EnableHighDpiScaling) # Not needed in PySide6
# QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps) # Not needed in PySide6
from ui.main_window import MainWindow

if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    # Set Application Icon
    if os.path.exists('logo.ico'):
        app.setWindowIcon(QIcon('logo.ico'))
        
    w = MainWindow()
    w.show()
    sys.exit(app.exec())
