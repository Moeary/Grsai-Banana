import sys
import os
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt

# Enable High DPI support
QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)

from ui.main_window import MainWindow

if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    # Set Application Icon
    if os.path.exists('logo.ico'):
        app.setWindowIcon(QIcon('logo.ico'))
        
    w = MainWindow()
    w.show()
    sys.exit(app.exec_())
