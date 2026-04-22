import os
from PySide6.QtCore import Qt, QSize, Signal, QUrl, QTimer
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea, QFrame, QDialog, QTextBrowser, QMessageBox
from PySide6.QtGui import QPixmap, QDesktopServices, QIcon, QFontMetrics, QImageReader
from qfluentwidgets import (CardWidget, StrongBodyLabel, BodyLabel, CaptionLabel, 
                            TransparentPushButton, FluentIcon, ImageLabel, ScrollArea, MessageBoxBase, SubtitleLabel,
                            InfoBar, InfoBarPosition)

from core.history_manager import history_mgr
from core.config import cfg
from core.i18n import tr

class TaskDetailsDialog(MessageBoxBase):
    def __init__(self, task_data, parent=None):
        super().__init__(parent)
        self.titleLabel = SubtitleLabel(tr("history.task_details"), self)
        self.viewLayout.addWidget(self.titleLabel)
        
        # Content
        self.content = QTextBrowser()
        self.content.setOpenExternalLinks(True)
        self.content.setStyleSheet("background-color: transparent; border: none; padding: 10px;")
        
        # Format details with better styling
        status_color = "green" if task_data['status'] == "succeeded" else "red" if task_data['status'] == "failed" else "orange"
        
        html = f"""
        <style>
            body {{ font-family: Arial, sans-serif; }}
            .section {{ margin-bottom: 15px; }}
            .section-title {{ font-weight: bold; font-size: 12pt; margin-bottom: 5px; color: #0078D4; }}
            .label {{ font-weight: bold; color: #333; }}
            .value {{ color: #555; }}
            .prompt {{ background-color: #f5f5f5; padding: 10px; border-radius: 5px; border-left: 3px solid #0078D4; margin: 5px 0; }}
            .error {{ color: red; background-color: #ffe0e0; padding: 10px; border-radius: 5px; border-left: 3px solid red; }}
            .success {{ color: green; }}
            hr {{ border: none; border-top: 1px solid #ddd; margin: 10px 0; }}
        </style>
        
        <div class="section">
            <div class="section-title">📝 Prompt</div>
            <div class="prompt">{task_data['prompt']}</div>
        </div>
        
        <hr>
        
        <div class="section">
            <div class="section-title">⚙️ Configuration</div>
            <p><span class="label">Model:</span> <span class="value">{task_data['model']}</span></p>
            <p><span class="label">Size:</span> <span class="value">{task_data['image_size']}</span></p>
            <p><span class="label">Aspect Ratio:</span> <span class="value">{task_data['aspect_ratio']}</span></p>
        </div>
        
        <div class="section">
            <div class="section-title">📊 Status</div>
            <p><span class="label">Status:</span> <span class="value" style="color: {status_color}; font-weight: bold;">{task_data['status'].capitalize()}</span></p>
            <p><span class="label">Created At:</span> <span class="value">{task_data['created_at']}</span></p>
            <p><span class="label">Task ID:</span> <span class="value" style="font-family: monospace; font-size: 10pt;">{task_data['id']}</span></p>
        </div>
        """
        
        # Add error information if present
        if task_data['status'] == "failed":
            failure_reason = task_data.get('failure_reason', 'Unknown')
            error_msg = task_data.get('error_message', '')
            
            html += f"""
            <div class="section">
                <div class="section-title">❌ Error Information</div>
                <p><span class="label">Failure Reason:</span> <span class="value" style="color: red;">{failure_reason}</span></p>
            """
            
            if error_msg:
                # Truncate very long error messages for display
                if len(error_msg) > 500:
                    html += f"""<p><span class="label">Details:</span></p>
                    <div class="error">{error_msg[:500]}...</div>
                    <p style="color: #999; font-size: 9pt;">Error message truncated. Full message available in logs.</p>"""
                else:
                    html += f"""<p><span class="label">Details:</span></p>
                    <div class="error">{error_msg}</div>"""
            
            html += "</div>"
            
        self.content.setHtml(html)
        self.content.setFixedHeight(400)
        self.content.setReadOnly(True)
        
        self.viewLayout.addWidget(self.content)
        
        self.yesButton.setText(tr("history.close"))
        self.cancelButton.hide()
        self.widget.setMinimumWidth(600)
        self.widget.setMinimumHeight(500)

class ClickableLabel(QLabel):
    clicked = Signal()
    def mousePressEvent(self, event):
        self.clicked.emit()

class HistoryItem(CardWidget):
    regenerateRequested = Signal(dict)
    THUMBNAIL_READ_SIZE = QSize(176, 176)

    def __init__(self, task_data, parent=None):
        super().__init__(parent)
        self.task_data = task_data
        self._thumbnail_loaded = False
        self._thumb_path = None
        self.setFixedHeight(120)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        
        # Thumbnail - Use standard QLabel to ensure fixed size works reliably
        self.thumb = QLabel()
        self.thumb.setFixedSize(88, 88)
        self.thumb.setStyleSheet("background-color: #eee; border-radius: 8px; border: 1px solid #ddd;")
        self.thumb.setScaledContents(True)
        
        if task_data["status"] == "succeeded" and task_data["result_path"] and os.path.exists(task_data["result_path"]):
            self._thumb_path = task_data["result_path"]
            self.thumb.setCursor(Qt.PointingHandCursor)
            self.thumb.mousePressEvent = self.on_thumb_click
            self.thumb.setText("...")
            self.thumb.setAlignment(Qt.AlignCenter)
        else:
            self.thumb.setText(tr("history.no_image"))
            self.thumb.setAlignment(Qt.AlignCenter)
            
        layout.addWidget(self.thumb)
        
        # Info
        info_layout = QVBoxLayout()
        info_layout.setSpacing(4)
        
        # Prompt Label - Clickable and Elided
        self.prompt_label = ClickableLabel()
        self.prompt_label.setCursor(Qt.PointingHandCursor)
        self.prompt_label.clicked.connect(self.show_details)
        
        # Elide text
        font = StrongBodyLabel().font()
        self.prompt_label.setFont(font)
        metrics = QFontMetrics(font)
        elided_text = metrics.elidedText(task_data["prompt"], Qt.ElideRight, 400) # Approx width
        self.prompt_label.setText(elided_text)
        # Tooltip for quick view
        self.prompt_label.setToolTip(tr("history.prompt_tooltip"))
        
        info_layout.addWidget(self.prompt_label)
        info_layout.addWidget(BodyLabel(f"Model: {task_data['model']} | Size: {task_data['image_size']}"))
        info_layout.addWidget(CaptionLabel(task_data["created_at"]))
        
        layout.addLayout(info_layout)
        layout.addStretch()
        
        # Status
        status_layout = QVBoxLayout()
        status_layout.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        
        status_text = task_data["status"].capitalize()
        status_label = StrongBodyLabel(status_text)
        if task_data["status"] == "succeeded":
            status_label.setStyleSheet("color: green;")
        elif task_data["status"] == "failed":
            status_label.setStyleSheet("color: red;")
        else:
            status_label.setStyleSheet("color: orange;")
            
        status_layout.addWidget(status_label)
        
        # Buttons Layout
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(5)
        
        # Regenerate Button
        regen_btn = TransparentPushButton(FluentIcon.SYNC, tr("history.regenerate"))
        regen_btn.setToolTip(tr("history.regenerate"))
        regen_btn.clicked.connect(self.on_regenerate)
        btn_layout.addWidget(regen_btn)

        if task_data["status"] == "succeeded" and task_data["result_path"]:
            open_btn = TransparentPushButton(FluentIcon.FOLDER, tr("history.open_folder"))
            open_btn.clicked.connect(self.open_folder)
            btn_layout.addWidget(open_btn)
            
        status_layout.addLayout(btn_layout)
        layout.addLayout(status_layout)

    def on_regenerate(self):
        self.regenerateRequested.emit(self.task_data)

    def show_details(self):
        w = TaskDetailsDialog(self.task_data, self.window())
        w.exec_()

    def on_thumb_click(self, event):
        if self.task_data["result_path"] and os.path.exists(self.task_data["result_path"]):
            # Open with system default viewer
            QDesktopServices.openUrl(QUrl.fromLocalFile(self.task_data["result_path"]))

    def open_folder(self):
        if self.task_data["result_path"]:
            folder = os.path.dirname(self.task_data["result_path"])
            QDesktopServices.openUrl(QUrl.fromLocalFile(folder))

    def has_thumbnail(self):
        return bool(self._thumb_path)

    def load_thumbnail(self):
        if self._thumbnail_loaded or not self._thumb_path:
            return

        reader = QImageReader(self._thumb_path)
        reader.setAutoTransform(True)

        source_size = reader.size()
        if source_size.isValid() and source_size.width() > 0 and source_size.height() > 0:
            reader.setScaledSize(source_size.scaled(self.THUMBNAIL_READ_SIZE, Qt.KeepAspectRatio))
        else:
            reader.setScaledSize(self.THUMBNAIL_READ_SIZE)

        image = reader.read()
        if not image.isNull():
            self.thumb.setText("")
            self.thumb.setPixmap(QPixmap.fromImage(image))
        else:
            self.thumb.setText(tr("history.no_image"))
        self._thumbnail_loaded = True

    def cleanup(self):
        self.thumb.clear()
        self.thumb.setPixmap(QPixmap())
        self._thumbnail_loaded = True
        self._thumb_path = None
            
class HistoryPage(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("HistoryPage")
        self.current_page = 1
        self.items_per_page = cfg.get("history_items_per_page", 5)
        self._thumbnail_queue = []
        self._load_token = 0
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Top bar with Refresh
        top_layout = QHBoxLayout()
        top_layout.setContentsMargins(20, 10, 20, 0)
        top_layout.addStretch()
        self.clear_running_btn = TransparentPushButton(FluentIcon.DELETE, tr("history.clear_running"))
        self.clear_running_btn.clicked.connect(self.clear_running_tasks)
        top_layout.addWidget(self.clear_running_btn)
        self.clear_failed_btn = TransparentPushButton(FluentIcon.DELETE, tr("history.clear_failed"))
        self.clear_failed_btn.clicked.connect(self.clear_failed_tasks)
        top_layout.addWidget(self.clear_failed_btn)
        self.clear_all_btn = TransparentPushButton(FluentIcon.DELETE, tr("history.clear_all"))
        self.clear_all_btn.clicked.connect(self.clear_all_tasks)
        top_layout.addWidget(self.clear_all_btn)
        self.refresh_btn = TransparentPushButton(FluentIcon.SYNC, tr("history.refresh"))
        self.refresh_btn.clicked.connect(self.refresh_data)
        top_layout.addWidget(self.refresh_btn)
        layout.addLayout(top_layout)
        
        self.scroll = ScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("QScrollArea { border: none; background-color: transparent; }")
        
        self.container = QWidget()
        self.container.setStyleSheet("background-color: transparent;")
        self.vbox = QVBoxLayout(self.container)
        self.vbox.setSpacing(10)
        self.vbox.setAlignment(Qt.AlignTop)
        
        self.scroll.setWidget(self.container)
        layout.addWidget(self.scroll)
        
        # Pagination
        pagination_layout = QHBoxLayout()
        pagination_layout.setContentsMargins(0, 10, 0, 10)
        pagination_layout.setAlignment(Qt.AlignCenter)
        
        self.prev_btn = TransparentPushButton(FluentIcon.LEFT_ARROW, tr("history.previous"))
        self.prev_btn.clicked.connect(self.prev_page)
        
        self.page_label = StrongBodyLabel("1 / 1")
        
        self.next_btn = TransparentPushButton(FluentIcon.RIGHT_ARROW, tr("history.next"))
        self.next_btn.clicked.connect(self.next_page)
        
        pagination_layout.addWidget(self.prev_btn)
        pagination_layout.addSpacing(20)
        pagination_layout.addWidget(self.page_label)
        pagination_layout.addSpacing(20)
        pagination_layout.addWidget(self.next_btn)
        
        layout.addLayout(pagination_layout)
        
    def showEvent(self, event):
        self.load_history()
        super().showEvent(event)

    def refresh_data(self):
        self.current_page = 1
        self.load_history()

    def _confirm_cleanup(self, title_key, content_key):
        reply = QMessageBox.question(
            self,
            tr(title_key),
            tr(content_key),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        return reply == QMessageBox.StandardButton.Yes

    def _show_cleanup_result(self, deleted_count):
        InfoBar.success(
            title=tr("common.success"),
            content=tr("history.clear_done", count=deleted_count),
            parent=self,
            position=InfoBarPosition.TOP_RIGHT,
        )

    def clear_failed_tasks(self):
        if not self._confirm_cleanup("history.clear_failed", "history.clear_failed_confirm"):
            return
        deleted_count = history_mgr.clear_failed_tasks()
        self.current_page = 1
        self.load_history()
        self._show_cleanup_result(deleted_count)

    def clear_running_tasks(self):
        if not self._confirm_cleanup("history.clear_running", "history.clear_running_confirm"):
            return
        deleted_count = history_mgr.clear_running_tasks()
        self.current_page = 1
        self.load_history()
        self._show_cleanup_result(deleted_count)

    def clear_all_tasks(self):
        if not self._confirm_cleanup("history.clear_all", "history.clear_all_confirm"):
            return
        if not self._confirm_cleanup("history.clear_all", "history.clear_all_second_confirm"):
            return
        deleted_count = history_mgr.clear_all_tasks()
        self.current_page = 1
        self.load_history()
        self._show_cleanup_result(deleted_count)

    def prev_page(self):
        if self.current_page > 1:
            self.current_page -= 1
            self.load_history()

    def next_page(self):
        self.current_page += 1
        self.load_history()

    def load_history(self):
        self._load_token += 1
        token = self._load_token
        self._thumbnail_queue = []

        # Clear existing widgets and release image memory promptly.
        while self.vbox.count():
            item = self.vbox.takeAt(0)
            if item is None:
                continue
            widget = item.widget()
            if widget:
                if hasattr(widget, "cleanup"):
                    widget.cleanup()
                widget.deleteLater()

        total_items = history_mgr.get_task_count()
        total_pages = (total_items + self.items_per_page - 1) // self.items_per_page
        if total_pages == 0: total_pages = 1
        
        if self.current_page > total_pages:
            self.current_page = total_pages
        if self.current_page < 1:
            self.current_page = 1
            
        current_tasks = history_mgr.get_tasks_page(self.current_page, self.items_per_page)
        
        if not current_tasks:
            self.vbox.addWidget(BodyLabel(tr("history.no_history")))
        else:
            for task in current_tasks:
                item = HistoryItem(task)
                item.regenerateRequested.connect(self.on_regenerate_requested)
                self.vbox.addWidget(item)
                if item.has_thumbnail():
                    self._thumbnail_queue.append(item)
            QTimer.singleShot(0, lambda: self._load_next_thumbnail(token))
        
        # Update Pagination Controls
        self.page_label.setText(f"{self.current_page} / {total_pages}")
        self.prev_btn.setEnabled(self.current_page > 1)
        self.next_btn.setEnabled(self.current_page < total_pages)

    def on_regenerate_requested(self, task_data):
        # Signal up to main window
        if self.window():
            self.window().regenerate_task(task_data)

    def _load_next_thumbnail(self, token):
        if token != self._load_token:
            return
        if not self._thumbnail_queue:
            return

        item = self._thumbnail_queue.pop(0)
        if item and item.parent() is not None:
            item.load_thumbnail()

        if self._thumbnail_queue and token == self._load_token:
            QTimer.singleShot(18, lambda: self._load_next_thumbnail(token))
