import os
import base64
from datetime import datetime
from PySide6.QtCore import Qt, Signal, QUrl, QSize, QTimer
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFileDialog, 
                               QFrame, QSizePolicy, QToolButton, QScrollArea, QApplication, QPlainTextEdit, QStackedWidget)
from PySide6.QtGui import QPixmap, QDragEnterEvent, QDropEvent, QImage, QIcon, QDesktopServices, QFont, QTextOption
from qfluentwidgets import (CardWidget, PrimaryPushButton, ComboBox, TextEdit, 
                            ImageLabel, StrongBodyLabel, CaptionLabel, InfoBar, InfoBarPosition, 
                            FluentIcon, TransparentToolButton, ProgressRing, BodyLabel, CheckBox)

from core.config import cfg
from core.task_manager import task_manager, TaskWorker


class ImageThumbnail(QWidget):
    removed = Signal(str)

    def __init__(self, path, parent=None):
        super().__init__(parent)
        self.path = path
        self.setFixedSize(100, 100)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0,0,0,0)
        
        self.img_label = QLabel()
        self.img_label.setScaledContents(True)
        self.img_label.setStyleSheet("border-radius: 8px; border: 1px solid #ddd;")
        
        pixmap = QPixmap(path)
        if not pixmap.isNull():
             self.img_label.setPixmap(pixmap)
        
        layout.addWidget(self.img_label)
        
        # Close button overlay
        self.close_btn = TransparentToolButton(FluentIcon.CLOSE, self)
        self.close_btn.setFixedSize(24, 24)
        self.close_btn.move(72, 4)
        self.close_btn.clicked.connect(self.on_remove)
        
    def on_remove(self):
        self.removed.emit(self.path)

class ImageDropArea(QFrame):
    imageDropped = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setFrameStyle(QFrame.StyledPanel | QFrame.Sunken)
        self.setStyleSheet("QFrame { border: 2px dashed #aaa; border-radius: 10px; background-color: transparent; }")
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        # Container for content
        self.content_widget = QWidget(self)
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setAlignment(Qt.AlignCenter)
        
        self.label = QLabel("Drag & Drop Images Here\n(Max 13)\nOr Click to Select\n(Ctrl+V to Paste)")
        self.label.setAlignment(Qt.AlignCenter)
        self.content_layout.addWidget(self.label)
        
        # Scroll Area for thumbnails
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("background: transparent; border: none;")
        self.scroll_area.setFixedHeight(120)
        self.scroll_area.hide()
        
        self.scroll_content = QWidget()
        self.scroll_content.setStyleSheet("background: transparent;")
        self.scroll_layout = QHBoxLayout(self.scroll_content)
        self.scroll_layout.setAlignment(Qt.AlignLeft)
        self.scroll_layout.setContentsMargins(10, 5, 10, 5)
        self.scroll_layout.setSpacing(10)
        
        self.scroll_area.setWidget(self.scroll_content)
        self.content_layout.addWidget(self.scroll_area)
        
        self.layout.addWidget(self.content_widget)
        
        # Clear All button (top right)
        self.clear_btn = TransparentToolButton(FluentIcon.DELETE, self)
        self.clear_btn.setFixedSize(30, 30)
        self.clear_btn.setToolTip("Clear All Images")
        self.clear_btn.move(self.width() - 35, 5)
        self.clear_btn.clicked.connect(self.clear_images)
        self.clear_btn.hide()
        
        # Paste button (bottom right)
        self.paste_btn = TransparentToolButton(FluentIcon.PASTE, self)
        self.paste_btn.setFixedSize(30, 30)
        self.paste_btn.setToolTip("Paste from Clipboard")
        self.paste_btn.clicked.connect(self.paste_from_clipboard)
        
        self.image_paths = []

    def resizeEvent(self, event):
        self.clear_btn.move(self.width() - 35, 5)
        self.paste_btn.move(self.width() - 35, self.height() - 35)
        super().resizeEvent(event)

    def paste_from_clipboard(self):
        clipboard = QApplication.clipboard()
        mime_data = clipboard.mimeData()
        
        if mime_data.hasImage():
            image = clipboard.image()
            if not image.isNull():
                import tempfile
                temp_dir = tempfile.gettempdir()
                temp_path = os.path.join(temp_dir, f"paste_image_{int(datetime.now().timestamp())}.png")
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
            pass

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
        thumb = ImageThumbnail(path)
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
            self.clear_btn.show()
            self.clear_btn.raise_()
        else:
            self.label.show()
            self.scroll_area.hide()
            self.clear_btn.hide()


class TaskWidget(QFrame):
    retry_requested = Signal(object)

    def __init__(self, index, prompt, params, parent=None):
        super().__init__(parent)
        self.index = index
        self.prompt = prompt
        self.params = params
        self.retry_count = 0
        self.attempt_count = 0  # Total attempts including retries
        self.max_retries = cfg.get("max_retries", 5)
        self.auto_retry = False
        self.retry_timer = QTimer()
        self.retry_timer.setSingleShot(True)
        self.retry_timer.timeout.connect(self.perform_auto_retry)
        self.status_text = "Pending"
        self.result_path = None
        
        self.setFixedHeight(80)
        self.setStyleSheet("TaskWidget { border: 1px solid #e0e0e0; border-radius: 8px; background-color: rgba(255, 255, 255, 0.05); }")
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(15)
        
        self.index_label = StrongBodyLabel(f"#{index}")
        self.index_label.setFixedWidth(40)
        layout.addWidget(self.index_label)
        
        # Show attempt info instead of prompt
        self.status_label = BodyLabel("Attempt: 1")
        layout.addWidget(self.status_label, 1)
        
        # Use QStackedWidget to manage state display (progress, result, or retry)
        self.status_stack = QStackedWidget()
        self.status_stack.setFixedSize(50, 50)
        
        # State 0: Progress
        self.progress_ring = ProgressRing()
        self.progress_ring.setFixedSize(50, 50)
        self.progress_ring.setTextVisible(True)
        self.status_stack.addWidget(self.progress_ring)
        
        # State 1: Result button
        self.result_btn = TransparentToolButton(FluentIcon.PHOTO, self)
        self.result_btn.setFixedSize(50, 50)
        self.result_btn.setIconSize(QSize(40, 40))
        self.result_btn.clicked.connect(self.open_image)
        self.status_stack.addWidget(self.result_btn)
        
        # State 2: Retry button
        self.retry_btn = TransparentToolButton(FluentIcon.SYNC, self)
        self.retry_btn.setFixedSize(50, 50)
        self.retry_btn.setIconSize(QSize(30, 30))
        self.retry_btn.setToolTip("Retry")
        self.retry_btn.clicked.connect(self.on_retry_click)
        self.status_stack.addWidget(self.retry_btn)
        
        # Show progress by default
        self.status_stack.setCurrentIndex(0)
        layout.addWidget(self.status_stack)
        
    def update_progress(self, value, status):
        # Show progress ring
        self.status_stack.setCurrentIndex(0)
        self.progress_ring.setValue(value)
        self.status_text = status
        self.status_label.setText(f"Attempt {self.attempt_count + 1}: {status}")
        self.progress_ring.setToolTip(f"Status: {status}")
        
    def set_success(self, filepath):
        self.result_path = filepath
        self.status_stack.setCurrentIndex(1)
        
        # Update status label
        if self.attempt_count == 0:
            self.status_label.setText("✓ Success on 1st attempt")
        elif self.attempt_count == 1:
            self.status_label.setText("✓ Success on retry 1")
        else:
            self.status_label.setText(f"✓ Success on retry {self.attempt_count}")
        
        pixmap = QPixmap(filepath)
        if not pixmap.isNull():
            icon = QIcon(pixmap)
            self.result_btn.setIcon(icon)
            
        self.setStyleSheet("TaskWidget { border: 1px solid #90EE90; border-radius: 8px; background-color: rgba(255, 255, 255, 0.1); }")

    def set_failed(self, reason):
        try:
            self.status_stack.setCurrentIndex(2)
            self.retry_btn.setToolTip(f"Failed: {reason}. Click to retry.")
            self.status_label.setText(f"✗ Failed: {reason}")
            self.setStyleSheet("TaskWidget { border: 1px solid #FFB6C1; border-radius: 8px; background-color: rgba(255, 255, 255, 0.1); }")
            
            if self.auto_retry and self.retry_count < self.max_retries:
                print(f"[TaskWidget] Auto-retrying... ({self.retry_count + 1}/{self.max_retries})")
                self.retry_count += 1
                self.attempt_count += 1
                # Delay retry by 1 second to ensure proper cleanup
                self.retry_timer.start(1000)
        except Exception as e:
            print(f"[TaskWidget] Error in set_failed: {e}")
    
    def perform_auto_retry(self):
        """Called by timer to safely perform auto-retry"""
        try:
            self.retry_requested.emit(self)
        except Exception as e:
            print(f"[TaskWidget] Error in perform_auto_retry: {e}")

    def on_retry_click(self):
        self.progress_ring.show()
        self.progress_ring.setValue(0)
        self.retry_btn.hide()
        self.retry_count += 1
        self.attempt_count += 1
        self.status_label.setText(f"Attempt {self.attempt_count + 1}: Retrying...")
        self.retry_requested.emit(self)

    def open_image(self):
        if self.result_path:
            QDesktopServices.openUrl(QUrl.fromLocalFile(self.result_path))


class GeneratorPage(QWidget):
    """UI-only generator page. Core logic is in TaskManager"""
    
    def __init__(self):
        super().__init__()
        self.setObjectName("GeneratorPage")
        self.task_counter = 0
        self.initUI()

    def initUI(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)
        
        # Left Side (2/3 width)
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(15)
        
        # Top: Prompt Section
        prompt_label_layout = QHBoxLayout()
        prompt_label_layout.addWidget(StrongBodyLabel("Prompt"))
        prompt_label_layout.addStretch()
        
        # Prompt toolbar buttons
        paste_btn = TransparentToolButton(FluentIcon.PASTE)
        paste_btn.setToolTip("Paste from clipboard")
        paste_btn.clicked.connect(self.paste_to_prompt)
        prompt_label_layout.addWidget(paste_btn)
        
        format_btn = TransparentToolButton(FluentIcon.FONT)
        format_btn.setToolTip("Apply text formatting")
        format_btn.clicked.connect(self.apply_prompt_formatting)
        prompt_label_layout.addWidget(format_btn)
        
        clear_btn = TransparentToolButton(FluentIcon.DELETE)
        clear_btn.setToolTip("Clear prompt")
        clear_btn.clicked.connect(lambda: self.prompt_edit.clear())
        prompt_label_layout.addWidget(clear_btn)
        
        left_layout.addLayout(prompt_label_layout)
        
        self.prompt_edit = TextEdit()
        self.prompt_edit.setPlaceholderText("Enter your prompt here...")
        self.prompt_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.prompt_edit.setMinimumHeight(150)
        
        # Apply text formatting if enabled
        self._apply_text_formatting()
        
        left_layout.addWidget(self.prompt_edit, 1)  # Stretch to fill available space
        
        # Bottom Section (Images + Settings) - stays at bottom
        bottom_section = QWidget()
        bottom_layout = QHBoxLayout(bottom_section)
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        bottom_layout.setSpacing(15)
        
        # Bottom Left: Images
        img_container = QWidget()
        img_layout = QVBoxLayout(img_container)
        img_layout.setContentsMargins(0, 0, 0, 0)
        img_layout.addWidget(StrongBodyLabel("Reference Images"))
        
        self.drop_area = ImageDropArea()
        self.drop_area.setFixedHeight(200)
        img_layout.addWidget(self.drop_area)
        
        bottom_layout.addWidget(img_container, 1)
        
        # Bottom Right: Settings
        settings_container = QWidget()
        settings_layout_v = QVBoxLayout(settings_container)
        settings_layout_v.setContentsMargins(0, 0, 0, 0)
        
        settings_card = CardWidget()
        settings_inner = QVBoxLayout(settings_card)
        
        # Model
        settings_inner.addWidget(CaptionLabel("Model"))
        self.model_combo = ComboBox()
        self.model_combo.addItems(["nano-banana-fast", "nano-banana", "nano-banana-pro"])
        self.model_combo.setCurrentText(cfg.get("last_model"))
        settings_inner.addWidget(self.model_combo)

        # Aspect Ratio
        settings_inner.addWidget(CaptionLabel("Aspect Ratio"))
        self.ratio_combo = ComboBox()
        self.ratio_combo.addItems(["auto", "1:1", "16:9", "9:16", "4:3", "3:4", "3:2", "2:3", "5:4", "4:5", "21:9"])
        self.ratio_combo.setCurrentText(cfg.get("last_aspect_ratio"))
        settings_inner.addWidget(self.ratio_combo)

        # Image Size
        settings_inner.addWidget(CaptionLabel("Image Size"))
        self.size_combo = ComboBox()
        self.size_combo.addItems(["1K", "2K", "4K"])
        self.size_combo.setCurrentText(cfg.get("last_image_size"))
        settings_inner.addWidget(self.size_combo)
        
        # Auto Retry
        self.auto_retry_cb = CheckBox("Auto Retry on Failure")
        self.auto_retry_cb.setChecked(False)
        settings_inner.addWidget(self.auto_retry_cb)
        
        settings_layout_v.addWidget(settings_card)
        
        # Generate Button
        self.gen_btn = PrimaryPushButton("Generate Image")
        self.gen_btn.clicked.connect(self.on_generate)
        self.gen_btn.setFixedHeight(40)
        settings_layout_v.addWidget(self.gen_btn)
        
        bottom_layout.addWidget(settings_container, 1)
        
        left_layout.addWidget(bottom_section)
        
        main_layout.addWidget(left_panel, 2)

        # Right Side (1/3 width) - Task List
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        right_layout.addWidget(StrongBodyLabel("Task List"))
        
        self.task_scroll = QScrollArea()
        self.task_scroll.setWidgetResizable(True)
        self.task_scroll.setStyleSheet("background: transparent; border: none;")
        
        self.task_container = QWidget()
        self.task_container.setStyleSheet("background: transparent;")
        self.task_layout = QVBoxLayout(self.task_container)
        self.task_layout.setAlignment(Qt.AlignTop)
        self.task_layout.setSpacing(10)
        
        self.task_scroll.setWidget(self.task_container)
        right_layout.addWidget(self.task_scroll)
        
        main_layout.addWidget(right_panel, 1)

    def keyPressEvent(self, event):
        if event.modifiers() == Qt.ControlModifier and event.key() == Qt.Key_V:
            clipboard = QApplication.clipboard()
            mime_data = clipboard.mimeData()
            if mime_data.hasImage():
                image = clipboard.image()
                if not image.isNull():
                    import tempfile
                    temp_dir = tempfile.gettempdir()
                    temp_path = os.path.join(temp_dir, f"paste_image_{int(datetime.now().timestamp())}.png")
                    image.save(temp_path, "PNG")
                    self.drop_area.add_image(temp_path)
                    InfoBar.success(title="Pasted", content="Image pasted from clipboard.", parent=self, position=InfoBarPosition.TOP_RIGHT)
            elif mime_data.hasUrls():
                for url in mime_data.urls():
                    path = url.toLocalFile()
                    if path.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                        self.drop_area.add_image(path)

    def paste_to_prompt(self):
        """Paste text from clipboard to prompt"""
        clipboard = QApplication.clipboard()
        text = clipboard.text()
        if text:
            self.prompt_edit.insertPlainText(text)
            self.apply_prompt_formatting()
            InfoBar.success(title="Pasted", content="Text pasted to prompt.", parent=self, position=InfoBarPosition.TOP_RIGHT)

    def apply_prompt_formatting(self):
        """Apply text formatting to prompt_edit"""
        self._apply_text_formatting()
        if cfg.get("text_format_enabled", False):
            InfoBar.success(title="Formatting Applied", content="Text formatting updated.", parent=self, position=InfoBarPosition.TOP_RIGHT)
        else:
            InfoBar.warning(title="Formatting Disabled", content="Enable text formatting in settings.", parent=self, position=InfoBarPosition.TOP_RIGHT)

    def _apply_text_formatting(self):
        """Apply text formatting settings to prompt_edit"""
        if cfg.get("text_format_enabled", False):
            # Get formatting settings
            font_size = cfg.get("text_font_size", 12)
            auto_wrap = cfg.get("text_auto_wrap", True)
            
            # Apply font size
            font = QFont()
            font.setPointSize(font_size)
            self.prompt_edit.setFont(font)
            
            # Apply text wrapping
            if auto_wrap:
                self.prompt_edit.setWordWrapMode(QTextOption.WordWrap)
            else:
                self.prompt_edit.setWordWrapMode(QTextOption.NoWrap)

    def update_text_formatting(self):
        """Update text formatting when settings change"""
        self._apply_text_formatting()

    def on_generate(self):
        prompt = self.prompt_edit.toPlainText().strip()
        if not prompt:
            InfoBar.warning(title="Warning", content="Please enter a prompt.", parent=self, position=InfoBarPosition.TOP_RIGHT)
            return

        model = self.model_combo.currentText()
        ratio = self.ratio_combo.currentText()
        size = self.size_combo.currentText()
        
        cfg.set("last_model", model)
        cfg.set("last_aspect_ratio", ratio)
        cfg.set("last_image_size", size)

        ref_urls = []
        for img_path in self.drop_area.image_paths:
            try:
                with open(img_path, "rb") as img_file:
                    b64_string = base64.b64encode(img_file.read()).decode('utf-8')
                    ext = os.path.splitext(img_path)[1].lower().replace('.', '')
                    if ext == 'jpg': ext = 'jpeg'
                    data_uri = f"data:image/{ext};base64,{b64_string}"
                    ref_urls.append(data_uri)
            except Exception as e:
                print(f"Error processing image {img_path}: {e}")

        params = {
            "model": model,
            "ratio": ratio,
            "size": size,
            "ref_urls": ref_urls
        }
        
        self.create_task(prompt, params)

    def create_task(self, prompt, params):
        self.task_counter += 1
        task_widget = TaskWidget(self.task_counter, prompt, params)
        task_widget.auto_retry = self.auto_retry_cb.isChecked()
        task_widget.retry_requested.connect(self.retry_task)
        
        self.task_layout.insertWidget(0, task_widget)
        
        self.start_worker(task_widget)

    def start_worker(self, task_widget):
        try:
            worker = task_manager.create_worker(
                task_widget.prompt, 
                task_widget.params["model"], 
                task_widget.params["ratio"], 
                task_widget.params["size"], 
                task_widget.params["ref_urls"]
            )
            
            # Ensure progress ring is visible
            task_widget.progress_ring.show()
            task_widget.progress_ring.setValue(0)
            task_widget.status_label.setText(f"Attempt {task_widget.attempt_count + 1}: Starting...")
            
            # Connect signals - these must remain connected for the entire lifetime
            worker.progress_signal.connect(task_widget.update_progress)
            worker.finished_signal.connect(lambda s, r, m: self.on_worker_finished(task_widget, s, r, m))
            worker.finished.connect(lambda: self.cleanup_worker(task_widget))
            
            task_manager.register_worker(task_widget, worker)
            print(f"[GeneratorPage] Starting new worker for task {task_widget.index}")
            worker.start()
        except Exception as e:
            print(f"[GeneratorPage] Error in start_worker: {e}")
            import traceback
            traceback.print_exc()

    def on_worker_finished(self, task_widget, success, result, msg):
        try:
            if success:
                task_widget.set_success(result)
            else:
                task_widget.set_failed(msg)
        except Exception as e:
            print(f"[GeneratorPage] Error in on_worker_finished: {e}")

    def cleanup_worker(self, task_widget):
        try:
            task_manager.unregister_worker(task_widget)
            print(f"[GeneratorPage] Cleaned up worker for task {task_widget.index}")
        except Exception as e:
            print(f"[GeneratorPage] Error in cleanup_worker: {e}")

    def retry_task(self, task_widget):
        try:
            self.start_worker(task_widget)
        except Exception as e:
            print(f"[GeneratorPage] Error in retry_task: {e}")
    
    def stop_all_workers(self):
        """Call from main window on close"""
        task_manager.stop_all_workers()
