import os
from datetime import datetime

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QImageReader, QPixmap
from PySide6.QtWidgets import QApplication, QFileDialog, QFrame, QLabel, QSizePolicy, QVBoxLayout, QWidget
from qfluentwidgets import InfoBar, InfoBarPosition, SingleDirectionScrollArea, TransparentToolButton, FluentIcon, isDarkTheme, qconfig

from core.i18n import tr


class ImageThumbnail(QWidget):
    removed = Signal(str)

    def __init__(self, path, drop_area=None):
        super().__init__()
        self.path = path
        self.drop_area = drop_area
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self._thumbnail_pixmap = self._load_thumbnail(path)
        if not self._thumbnail_pixmap.isNull() and self._thumbnail_pixmap.height() > 0:
            self.aspect_ratio = self._thumbnail_pixmap.width() / self._thumbnail_pixmap.height()
        else:
            self.aspect_ratio = 1.0

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.img_label = QLabel()
        self.img_label.setScaledContents(True)
        self.img_label.setAlignment(Qt.AlignCenter)
        self.img_label.setStyleSheet("border-radius: 8px; border: 1px solid #ddd;")
        if not self._thumbnail_pixmap.isNull():
            self.img_label.setPixmap(self._thumbnail_pixmap)

        layout.addWidget(self.img_label)

        self.close_btn = TransparentToolButton(FluentIcon.CLOSE, self)
        self.close_btn.setFixedSize(24, 24)
        self.close_btn.clicked.connect(self.on_remove)
        self.close_btn.raise_()

        self.update_size(force=True)

    def _load_thumbnail(self, path):
        reader = QImageReader(path)
        reader.setAutoTransform(True)

        source_size = reader.size()
        if source_size.isValid() and source_size.width() > 0 and source_size.height() > 0:
            target_size = source_size.scaled(1024, 1024, Qt.KeepAspectRatio)
            if target_size.isValid() and target_size.width() > 0 and target_size.height() > 0:
                reader.setScaledSize(target_size)

        image = reader.read()
        if image.isNull():
            return QPixmap(path)
        return QPixmap.fromImage(image)

    def _available_width(self):
        if self.drop_area and hasattr(self.drop_area, "scroll_area"):
            viewport = self.drop_area.scroll_area.viewport()
            if viewport is not None and viewport.width() > 0:
                return max(viewport.width() - 8, 100)
        if self.drop_area:
            return max(self.drop_area.width() - 26, 100)
        return 368

    def update_size(self, force=False):
        img_width = self._available_width()
        img_height = max(int(img_width / self.aspect_ratio), 80)

        if not force and self.img_label.width() == img_width and self.img_label.height() == img_height:
            return

        self.img_label.setFixedSize(img_width, img_height)
        self.setFixedHeight(img_height)
        self.close_btn.move(6, 6)

    def on_remove(self):
        self.removed.emit(self.path)


class ImageDropArea(QFrame):
    imageDropped = Signal(str)
    SUPPORTED_EXTENSIONS = (".png", ".jpg", ".jpeg", ".webp", ".bmp")
    MAX_IMAGES = 14

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setFrameStyle(QFrame.StyledPanel | QFrame.Sunken)

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(10, 10, 10, 10)

        self.content_widget = QWidget(self)
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setAlignment(Qt.AlignCenter)
        self.content_layout.setContentsMargins(0, 0, 0, 0)

        self.label = QLabel()
        self.label.setAlignment(Qt.AlignCenter)
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
        self.thumbnail_widgets = {}

        self.update_style()
        self.update_texts()
        qconfig.themeChanged.connect(self.update_style)

    def update_texts(self):
        self.label.setText(tr("drop.placeholder"))

    def update_style(self):
        if isDarkTheme():
            bg_color = "rgba(255, 255, 255, 0.06)"
            border_color = "rgba(255, 255, 255, 0.1)"
            label_color = "#cecece"
        else:
            bg_color = "rgb(255, 255, 255)"
            border_color = "rgba(0, 0, 0, 0.12)"
            label_color = "#606060"

        self.setStyleSheet(
            f"""
            QFrame {{
                border: 1px solid {border_color};
                border-radius: 6px;
                background-color: {bg_color};
            }}
            """
        )
        self.label.setStyleSheet(f"color: {label_color};")

    def resizeEvent(self, event):
        super().resizeEvent(event)
        for i in range(self.scroll_layout.count()):
            item = self.scroll_layout.itemAt(i)
            widget = item.widget()
            if isinstance(widget, ImageThumbnail):
                widget.update_size(force=True)

    def paste_from_clipboard(self):
        clipboard = QApplication.clipboard()
        mime_data = clipboard.mimeData()

        if mime_data.hasImage():
            image = clipboard.image()
            if not image.isNull():
                input_dir = os.path.join(os.getcwd(), "input")
                os.makedirs(input_dir, exist_ok=True)
                temp_path = os.path.join(input_dir, f"clipboard_{int(datetime.now().timestamp())}.png")
                image.save(temp_path, "PNG")
                added = self.add_images([temp_path], show_limit_warning=True)
                if added:
                    InfoBar.success(
                        title=tr("common.pasted"),
                        content=tr("drop.msg.pasted_image"),
                        parent=self,
                        position=InfoBarPosition.TOP_RIGHT,
                    )
                return

        if mime_data.hasUrls():
            paths = [url.toLocalFile() for url in mime_data.urls()]
            added = self.add_images(paths, show_limit_warning=True)
            if added:
                InfoBar.success(
                    title=tr("common.pasted"),
                    content=tr("drop.msg.pasted_files"),
                    parent=self,
                    position=InfoBarPosition.TOP_RIGHT,
                )
            else:
                InfoBar.warning(
                    title=tr("common.warning"),
                    content=tr("drop.msg.no_supported_image"),
                    parent=self,
                    position=InfoBarPosition.TOP_RIGHT,
                )
            return

        InfoBar.warning(
            title=tr("common.warning"),
            content=tr("drop.msg.no_image"),
            parent=self,
            position=InfoBarPosition.TOP_RIGHT,
        )

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls() or event.mimeData().hasImage():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent):
        if event.mimeData().hasUrls():
            paths = [url.toLocalFile() for url in event.mimeData().urls()]
            self.add_images(paths, show_limit_warning=True)
        event.acceptProposedAction()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            fnames, _ = QFileDialog.getOpenFileNames(self, tr("drop.dialog.open_files"), "", tr("drop.dialog.filter"))
            if fnames:
                self.add_images(fnames, show_limit_warning=True)

    def _is_supported_image(self, path):
        return bool(path) and path.lower().endswith(self.SUPPORTED_EXTENSIONS)

    def _create_thumbnail(self, path):
        thumb = ImageThumbnail(path, drop_area=self)
        thumb.removed.connect(self.remove_image)
        self.thumbnail_widgets[path] = thumb
        self.scroll_layout.addWidget(thumb)

    def add_images(self, paths, show_limit_warning=False):
        if not paths:
            return 0

        available_slots = max(self.MAX_IMAGES - len(self.image_paths), 0)
        if available_slots == 0:
            if show_limit_warning:
                InfoBar.warning(
                    title=tr("common.limit_reached"),
                    content=tr("drop.msg.limit_reached"),
                    parent=self,
                    position=InfoBarPosition.TOP_RIGHT,
                )
            return 0

        valid_new_paths = []
        for path in paths:
            if not self._is_supported_image(path):
                continue
            if path in self.image_paths or path in valid_new_paths:
                continue
            valid_new_paths.append(path)

        if not valid_new_paths:
            return 0

        overflow_count = max(len(valid_new_paths) - available_slots, 0)
        paths_to_add = valid_new_paths[:available_slots]

        self.setUpdatesEnabled(False)
        self.scroll_content.setUpdatesEnabled(False)
        try:
            for path in paths_to_add:
                self.image_paths.append(path)
                self._create_thumbnail(path)
        finally:
            self.scroll_content.setUpdatesEnabled(True)
            self.setUpdatesEnabled(True)

        self.update_ui_state()
        for path in paths_to_add:
            self.imageDropped.emit(path)

        if overflow_count > 0 and show_limit_warning:
            InfoBar.warning(
                title=tr("common.limit_reached"),
                content=tr("drop.msg.limit_skipped", count=overflow_count),
                parent=self,
                position=InfoBarPosition.TOP_RIGHT,
            )

        return len(paths_to_add)

    def add_image(self, path):
        self.add_images([path], show_limit_warning=True)

    def remove_image(self, path):
        if path in self.image_paths:
            self.image_paths.remove(path)
            widget = self.thumbnail_widgets.pop(path, None)
            if widget:
                widget.deleteLater()
            self.update_ui_state()

    def clear_images(self):
        self.image_paths = []
        self.thumbnail_widgets.clear()
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
