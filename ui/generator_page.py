import os
import base64
from PyQt5.QtCore import Qt, pyqtSignal, QThread, QUrl, QSize
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFileDialog, QFrame, QSizePolicy, QToolButton, QScrollArea
from PyQt5.QtGui import QPixmap, QDragEnterEvent, QDropEvent, QImage, QIcon
from qfluentwidgets import (CardWidget, PrimaryPushButton, ComboBox, TextEdit, 
                            ImageLabel, StrongBodyLabel, CaptionLabel, InfoBar, InfoBarPosition, FluentIcon, TransparentToolButton)

from core.config import cfg
from core.api_client import api
from core.history_manager import history_mgr

class ImageThumbnail(QWidget):
    removed = pyqtSignal(str)

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
             # Crop center or just scale? Scale keeping aspect ratio by expanding then crop is better but complex.
             # Simple scale for now
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
    imageDropped = pyqtSignal(str)

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
                from datetime import datetime
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
            # Handle raw image data if needed
            pass

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            # If clicking on empty space, open dialog
            # But we have thumbnails now, so we need to be careful not to block them?
            # The thumbnails are in scroll_area which is a child.
            # If we click on the frame but not on a child widget...
            # Actually QScrollArea will handle its own clicks.
            
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
            # Find widget and remove
            for i in range(self.scroll_layout.count()):
                item = self.scroll_layout.itemAt(i)
                widget = item.widget()
                if isinstance(widget, ImageThumbnail) and widget.path == path:
                    widget.deleteLater()
                    break
            self.update_ui_state()

    def clear_images(self):
        self.image_paths = []
        # Clear widgets
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

class AspectRatioLabel(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet("background-color: #f0f0f0; border: 1px solid #ddd; border-radius: 8px;")
        self._pixmap = None

    def setImage(self, path):
        if path and os.path.exists(path):
            self._pixmap = QPixmap(path)
            self.update_pixmap()
        else:
            self._pixmap = None
            self.clear()

    def resizeEvent(self, event):
        self.update_pixmap()
        super().resizeEvent(event)

    def update_pixmap(self):
        if self._pixmap and not self._pixmap.isNull():
            # Scale pixmap to fit the label size, keeping aspect ratio
            # Use a slightly smaller size to ensure borders are visible
            target_size = self.size() - QSize(4, 4) 
            scaled = self._pixmap.scaled(target_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            super().setPixmap(scaled)

class GeneratorPage(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("GeneratorPage")
        self.initUI()

    def initUI(self):
        main_layout = QHBoxLayout(self)
        
        # Left Side - Controls
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setSpacing(15)
        
        # Image Upload
        self.drop_area = ImageDropArea()
        self.drop_area.setFixedHeight(200)
        left_layout.addWidget(StrongBodyLabel("Reference Image (Optional)"))
        left_layout.addWidget(self.drop_area)

        # Prompt
        left_layout.addWidget(StrongBodyLabel("Prompt"))
        self.prompt_edit = TextEdit()
        self.prompt_edit.setPlaceholderText("Enter your prompt here...")
        self.prompt_edit.setFixedHeight(100)
        left_layout.addWidget(self.prompt_edit)

        # Settings
        settings_card = CardWidget()
        settings_layout = QVBoxLayout(settings_card)
        
        # Model
        settings_layout.addWidget(CaptionLabel("Model"))
        self.model_combo = ComboBox()
        self.model_combo.addItems(["nano-banana-fast", "nano-banana", "nano-banana-pro"])
        self.model_combo.setCurrentText(cfg.get("last_model"))
        settings_layout.addWidget(self.model_combo)

        # Aspect Ratio
        settings_layout.addWidget(CaptionLabel("Aspect Ratio"))
        self.ratio_combo = ComboBox()
        self.ratio_combo.addItems(["auto", "1:1", "16:9", "9:16", "4:3", "3:4", "3:2", "2:3", "5:4", "4:5", "21:9"])
        self.ratio_combo.setCurrentText(cfg.get("last_aspect_ratio"))
        settings_layout.addWidget(self.ratio_combo)

        # Image Size
        settings_layout.addWidget(CaptionLabel("Image Size"))
        self.size_combo = ComboBox()
        self.size_combo.addItems(["1K", "2K", "4K"])
        self.size_combo.setCurrentText(cfg.get("last_image_size"))
        settings_layout.addWidget(self.size_combo)

        left_layout.addWidget(settings_card)

        # Generate Button
        self.gen_btn = PrimaryPushButton("Generate Image")
        self.gen_btn.clicked.connect(self.on_generate)
        left_layout.addWidget(self.gen_btn)
        
        left_layout.addStretch()

        # Right Side - Preview
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        right_layout.addWidget(StrongBodyLabel("Result Image"))
        
        # Use a container for the image to handle resizing better
        self.image_container = QWidget()
        self.image_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        container_layout = QVBoxLayout(self.image_container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        
        self.preview_label = AspectRatioLabel()
        self.preview_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        
        container_layout.addWidget(self.preview_label)
        right_layout.addWidget(self.image_container, 1) # Give it stretch factor
        
        self.status_label = CaptionLabel("Ready")
        self.status_label.setAlignment(Qt.AlignCenter)
        right_layout.addWidget(self.status_label)
        
        # Splitter approach might be better but let's try adjusting stretch factors first
        # Left panel fixed width or max width?
        left_panel.setMaximumWidth(400)
        
        main_layout.addWidget(left_panel)
        main_layout.addWidget(right_panel, 1)

    def keyPressEvent(self, event):
        if event.modifiers() == Qt.ControlModifier and event.key() == Qt.Key_V:
            clipboard = QApplication.clipboard()
            mime_data = clipboard.mimeData()
            if mime_data.hasImage():
                image = clipboard.image()
                if not image.isNull():
                    # Save to a temporary file
                    import tempfile
                    temp_dir = tempfile.gettempdir()
                    temp_path = os.path.join(temp_dir, f"paste_image_{int(datetime.now().timestamp())}.png")
                    image.save(temp_path, "PNG")
                    self.drop_area.add_image(temp_path)
                    InfoBar.success(title="Pasted", content="Image pasted from clipboard.", parent=self, position=InfoBarPosition.TOP_RIGHT)
            elif mime_data.hasUrls():
                # Handle file copy-paste
                for url in mime_data.urls():
                    path = url.toLocalFile()
                    if path.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                        self.drop_area.add_image(path)
                        break

    def on_generate(self):
        prompt = self.prompt_edit.toPlainText().strip()
        if not prompt:
            InfoBar.warning(title="Warning", content="Please enter a prompt.", parent=self, position=InfoBarPosition.TOP_RIGHT)
            return

        model = self.model_combo.currentText()
        ratio = self.ratio_combo.currentText()
        size = self.size_combo.currentText()
        
        # Save settings
        cfg.set("last_model", model)
        cfg.set("last_aspect_ratio", ratio)
        cfg.set("last_image_size", size)

        # Handle Images
        ref_urls = []
        # self.drop_area.image_paths is a list now
        for img_path in self.drop_area.image_paths:
            try:
                with open(img_path, "rb") as img_file:
                    b64_string = base64.b64encode(img_file.read()).decode('utf-8')
                    # Guess mime type
                    ext = os.path.splitext(img_path)[1].lower().replace('.', '')
                    if ext == 'jpg': ext = 'jpeg'
                    data_uri = f"data:image/{ext};base64,{b64_string}"
                    ref_urls.append(data_uri)
            except Exception as e:
                print(f"Error processing image {img_path}: {e}")

        # Submit Task
        self.gen_btn.setEnabled(False)
        self.status_label.setText("Submitting task...")
        
        # Run in background to avoid freezing UI
        self.submit_thread = SubmitTaskThread(prompt, model, ratio, size, ref_urls)
        self.submit_thread.finished.connect(self.on_submit_finished)
        self.submit_thread.start()
        
        # Keep track of background threads
        if not hasattr(self, 'background_threads'):
            self.background_threads = []

    def on_submit_finished(self, result):
        self.gen_btn.setEnabled(True)
        if result.get("code") == 0:
            task_id = result["data"]["id"]
            InfoBar.success(title="Success", content="Task submitted successfully.", parent=self, position=InfoBarPosition.TOP_RIGHT)
            self.status_label.setText(f"Task ID: {task_id} - Waiting for results...")
            
            # Add to history
            # Pass the list of paths
            history_mgr.add_task(
                task_id, 
                self.prompt_edit.toPlainText(), 
                self.model_combo.currentText(),
                self.ratio_combo.currentText(),
                self.size_combo.currentText(),
                self.drop_area.image_paths
            )
            
            # If there was a previous polling thread active on the UI, disconnect it from UI updates
            if hasattr(self, 'current_poll_thread') and self.current_poll_thread.isRunning():
                try:
                    self.current_poll_thread.update_signal.disconnect(self.on_poll_update)
                    self.current_poll_thread.finished_signal.disconnect(self.on_poll_finished)
                except:
                    pass
            
            # Start polling for this specific task
            self.current_poll_thread = PollTaskThread(task_id)
            self.current_poll_thread.update_signal.connect(self.on_poll_update)
            self.current_poll_thread.finished_signal.connect(self.on_poll_finished)
            
            # Add to background threads to keep reference
            self.background_threads.append(self.current_poll_thread)
            
            # Clean up finished threads from list
            self.current_poll_thread.finished.connect(lambda: self.cleanup_thread(self.current_poll_thread))
            
            self.current_poll_thread.start()
            
        else:
            InfoBar.error(title="Error", content=f"Submission failed: {result.get('msg')}", parent=self, position=InfoBarPosition.TOP_RIGHT)
            self.status_label.setText("Submission failed.")

    def cleanup_thread(self, thread):
        if thread in self.background_threads:
            self.background_threads.remove(thread)

    def on_poll_update(self, progress, status):
        self.status_label.setText(f"Status: {status} - Progress: {progress}%")

    def on_poll_finished(self, task_id, success, result_path, msg):
        if success:
            self.status_label.setText("Generation Complete!")
            self.preview_label.setImage(result_path)
            InfoBar.success(title="Done", content="Image generated successfully.", parent=self, position=InfoBarPosition.TOP_RIGHT)
        else:
            self.status_label.setText(f"Failed: {msg}")
            InfoBar.error(title="Failed", content=msg, parent=self, position=InfoBarPosition.TOP_RIGHT)

class SubmitTaskThread(QThread):
    finished = pyqtSignal(dict)

    def __init__(self, prompt, model, ratio, size, ref_urls):
        super().__init__()
        self.prompt = prompt
        self.model = model
        self.ratio = ratio
        self.size = size
        self.ref_urls = ref_urls

    def run(self):
        res = api.submit_task(self.prompt, self.model, self.ratio, self.size, self.ref_urls)
        self.finished.emit(res)

class PollTaskThread(QThread):
    update_signal = pyqtSignal(int, str)
    finished_signal = pyqtSignal(str, bool, str, str)

    def __init__(self, task_id):
        super().__init__()
        self.task_id = task_id

    def run(self):
        import time
        import requests
        
        error_count = 0
        while True:
            try:
                res = api.get_task_result(self.task_id)
                error_count = 0 # Reset on success
            except Exception as e:
                error_count += 1
                if error_count > 5:
                    self.finished_signal.emit(self.task_id, False, "", f"Network error: {str(e)}")
                    return
                time.sleep(2)
                continue

            if res.get("code") != 0:
                # If task not found or other API error, maybe wait a bit or fail
                if res.get("code") == -22: # Task not found, maybe not ready yet?
                    time.sleep(2)
                    continue
                self.finished_signal.emit(self.task_id, False, "", res.get("msg", "Unknown error"))
                return

            data = res.get("data", {})
            status = data.get("status")
            progress = data.get("progress", 0)
            
            self.update_signal.emit(progress, status)

            if status == "succeeded":
                results = data.get("results", [])
                if results:
                    img_url = results[0].get("url")
                    # Download image
                    try:
                        img_data = requests.get(img_url).content
                        timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
                        ext = "png" # Default
                        if ".jpg" in img_url: ext = "jpg"
                        if ".jpeg" in img_url: ext = "jpeg"
                        
                        filename = f"{timestamp}.{ext}"
                        output_dir = cfg.get("output_folder")
                        if not os.path.exists(output_dir):
                            os.makedirs(output_dir)
                            
                        filepath = os.path.join(output_dir, filename)
                        with open(filepath, "wb") as f:
                            f.write(img_data)
                            
                        history_mgr.update_task(self.task_id, "succeeded", result_path=filepath, preview_url=img_url)
                        self.finished_signal.emit(self.task_id, True, filepath, "Success")
                    except Exception as e:
                        history_mgr.update_task(self.task_id, "failed", failure_reason=str(e))
                        self.finished_signal.emit(self.task_id, False, "", str(e))
                else:
                    history_mgr.update_task(self.task_id, "failed", failure_reason="No results found")
                    self.finished_signal.emit(self.task_id, False, "", "No results found")
                return

            elif status == "failed":
                reason = data.get("failure_reason", "Unknown")
                history_mgr.update_task(self.task_id, "failed", failure_reason=reason)
                self.finished_signal.emit(self.task_id, False, "", reason)
                return

            time.sleep(2)

from PyQt5.QtWidgets import QApplication
from datetime import datetime
