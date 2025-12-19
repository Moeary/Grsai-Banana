import os
from datetime import datetime
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFileDialog, 
                               QFrame, QSizePolicy, QApplication)
from PySide6.QtGui import QPixmap, QDragEnterEvent, QDropEvent, QImage, QIcon
from qfluentwidgets import (TransparentToolButton, FluentIcon, InfoBar, InfoBarPosition, 
                            SingleDirectionScrollArea, isDarkTheme, StrongBodyLabel, qconfig)

class ImageThumbnail(QWidget):
    removed = Signal(str)

    def __init__(self, path, drop_area=None):
        super().__init__()
        self.path = path
        self.drop_area = drop_area
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        
        self.image_obj = QImage(path)
        if not self.image_obj.isNull():
            self.original_width = self.image_obj.width()
            self.original_height = self.image_obj.height()
            self.aspect_ratio = self.original_width / self.original_height if self.original_height > 0 else 1.0
        else:
            self.original_width = 400
            self.original_height = 250
            self.aspect_ratio = 400 / 250
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.img_label = QLabel()
        self.img_label.setScaledContents(True)
        self.img_label.setStyleSheet("border-radius: 8px; border: 1px solid #ddd;")
        
        pixmap = QPixmap(path)
        if not pixmap.isNull():
            self.img_label.setPixmap(pixmap)
        
        layout.addWidget(self.img_label)
        layout.addStretch()
        
        self.close_btn = TransparentToolButton(FluentIcon.CLOSE, self)
        self.close_btn.setFixedSize(24, 24)
        self.close_btn.move(4, 4)
        self.close_btn.clicked.connect(self.on_remove)
        
        self.update_size()
        
    def update_size(self):
        if self.drop_area and hasattr(self.drop_area, 'width'):
            drop_area_width = self.drop_area.width()
            available_width = drop_area_width - 20 - 12
        else:
            available_width = 368
        
        img_width = max(available_width, 100)
        img_height = int(img_width / self.aspect_ratio)
        
        self.img_label.setFixedSize(img_width, img_height)
        self.setFixedHeight(img_height)
        
    def on_remove(self):
        self.removed.emit(self.path)

class ImageDropArea(QFrame):
    imageDropped = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setFrameStyle(QFrame.StyledPanel | QFrame.Sunken)
        
        # Style to match TextEdit (approximate)
        # Using a semi-transparent background that works for both light/dark or specific colors
        self.update_style()
        qconfig.themeChanged.connect(self.update_style)
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(10, 10, 10, 10)
        
        self.content_widget = QWidget(self)
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setAlignment(Qt.AlignCenter)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        
        self.label = QLabel("Drag & Drop Images Here\n(Max 13)\nOr Click to Select\n(Ctrl+V to Paste)")
        self.label.setAlignment(Qt.AlignCenter)
        # Set label color based on theme
        self.update_label_color()
        
        self.content_layout.addWidget(self.label)
        
        self.scroll_area = SingleDirectionScrollArea(orient=Qt.Vertical)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.hide()
        
        self.scroll_content = QWidget()
        self.scroll_content.setStyleSheet("QWidget { background: transparent; }")
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setAlignment(Qt.AlignTop)
        self.scroll_layout.setContentsMargins(0, 0, 0, 0)
        self.scroll_layout.setSpacing(10)
        
        self.scroll_area.setWidget(self.scroll_content)
        self.scroll_area.enableTransparentBackground()
        
        self.content_layout.addWidget(self.scroll_area)
        self.layout.addWidget(self.content_widget)
        
        self.image_paths = []

    def update_style(self):
        # Simple style that looks like an input field
        # In a real app with qfluentwidgets, we might want to hook into theme changes
        if isDarkTheme():
            bg_color = "rgba(255, 255, 255, 0.06)"
            border_color = "rgba(255, 255, 255, 0.1)"
        else:
            bg_color = "rgb(255, 255, 255)"
            border_color = "rgba(0, 0, 0, 0.12)"
            
        self.setStyleSheet(f"""
            QFrame {{ 
                border: 1px solid {border_color}; 
                border-radius: 6px; 
                background-color: {bg_color}; 
            }}
        """)

    def update_label_color(self):
        if isDarkTheme():
            self.label.setStyleSheet("color: #cecece;")
        else:
            self.label.setStyleSheet("color: #606060;")

    def resizeEvent(self, event):
        super().resizeEvent(event)
        for i in range(self.scroll_layout.count()):
            item = self.scroll_layout.itemAt(i)
            widget = item.widget()
            if isinstance(widget, ImageThumbnail):
                widget.update_size()

    def paste_from_clipboard(self):
        clipboard = QApplication.clipboard()
        mime_data = clipboard.mimeData()
        
        if mime_data.hasImage():
            image = clipboard.image()
            if not image.isNull():
                input_dir = os.path.join(os.getcwd(), "input")
                if not os.path.exists(input_dir):
                    os.makedirs(input_dir)
                temp_path = os.path.join(input_dir, f"clipboard_{int(datetime.now().timestamp())}.png")
                image.save(temp_path, "PNG")
                self.add_image(temp_path)
                InfoBar.success(title="Pasted", content="Image pasted from clipboard.", parent=self, position=InfoBarPosition.TOP_RIGHT)
                return

        if mime_data.hasUrls():
            for url in mime_data.urls():
                path = url.toLocalFile()
                if path.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                    self.add_image(path)
            InfoBar.success(title="Pasted", content="Image file(s) pasted from clipboard.", parent=self, position=InfoBarPosition.TOP_RIGHT)
            return
        
        InfoBar.warning(title="No Image", content="No image found in clipboard.", parent=self, position=InfoBarPosition.TOP_RIGHT)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls() or event.mimeData().hasImage():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                path = url.toLocalFile()
                if path.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                    self.add_image(path)
        elif event.mimeData().hasImage():
            pass # Handled by paste usually, or could implement direct drop

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            fnames, _ = QFileDialog.getOpenFileNames(self, 'Open files', '', "Image files (*.jpg *.jpeg *.png *.webp)")
            if fnames:
                for fname in fnames:
                    self.add_image(fname)

    def add_image(self, path):
        if len(self.image_paths) >= 13:
            InfoBar.warning(title="Limit Reached", content="Maximum 13 images allowed.", parent=self, position=InfoBarPosition.TOP_RIGHT)
            return
            
        if path in self.image_paths:
             return

        self.image_paths.append(path)
        thumb = ImageThumbnail(path, drop_area=self)
        thumb.removed.connect(self.remove_image)
        self.scroll_layout.addWidget(thumb)
        self.update_ui_state()
        self.imageDropped.emit(path)

    def remove_image(self, path):
        if path in self.image_paths:
            self.image_paths.remove(path)
            for i in range(self.scroll_layout.count()):
                item = self.scroll_layout.itemAt(i)
                widget = item.widget()
                if isinstance(widget, ImageThumbnail) and widget.path == path:
                    widget.deleteLater()
                    break
            self.update_ui_state()

    def clear_images(self):
        self.image_paths = []
        while self.scroll_layout.count():
            item = self.scroll_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.update_ui_state()
        self.imageDropped.emit("")

    def update_ui_state(self):
        if self.image_paths:
            self.label.hide()
            self.scroll_area.show()
        else:
            self.label.show()
            self.scroll_area.hide()
