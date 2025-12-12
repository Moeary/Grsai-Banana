from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QApplication
from qfluentwidgets import FluentWindow, NavigationItemPosition, FluentIcon, SplashScreen

from ui.generator_page import GeneratorPage
from ui.history_page import HistoryPage
from ui.settings_page import SettingsPage

class MainWindow(FluentWindow):
    def __init__(self):
        super().__init__()
        self.initWindow()

        # Create sub interfaces
        self.generator_interface = GeneratorPage()
        self.history_interface = HistoryPage()
        self.settings_interface = SettingsPage()

        self.initNavigation()
        # self.splashScreen.finish()

    def initWindow(self):
        self.resize(1100, 750)
        self.setMinimumWidth(760)
        self.setWindowTitle('Banana Image Generator')
        
        # Center on screen
        desktop = QApplication.desktop().availableGeometry()
        w, h = desktop.width(), desktop.height()
        self.move(w//2 - self.width()//2, h//2 - self.height()//2)

    def initNavigation(self):
        self.addSubInterface(self.generator_interface, FluentIcon.BRUSH, 'Generator')
        self.addSubInterface(self.history_interface, FluentIcon.HISTORY, 'History')
        self.addSubInterface(self.settings_interface, FluentIcon.SETTING, 'Settings', position=NavigationItemPosition.BOTTOM)

    def regenerate_task(self, task_data):
        # Switch to generator page
        self.switchTo(self.generator_interface)
        
        # Populate fields
        self.generator_interface.prompt_edit.setText(task_data['prompt'])
        self.generator_interface.model_combo.setCurrentText(task_data['model'])
        self.generator_interface.ratio_combo.setCurrentText(task_data['aspect_ratio'])
        self.generator_interface.size_combo.setCurrentText(task_data['image_size'])
        
        # Handle reference image if it exists
        # Clear existing images first
        self.generator_interface.drop_area.clear_images()
        
        if task_data.get('ref_images'):
            ref_imgs = task_data['ref_images']
            if isinstance(ref_imgs, str):
                self.generator_interface.drop_area.add_image(ref_imgs)
            elif isinstance(ref_imgs, list):
                for img_path in ref_imgs:
                    self.generator_interface.drop_area.add_image(img_path)
        
        # Do not trigger generation automatically, let user decide
        # self.generator_interface.on_generate()
