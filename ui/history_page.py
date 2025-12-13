import os
from PySide6.QtCore import Qt, QSize, Signal, QUrl
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea, QFrame, QDialog, QTextBrowser
from PySide6.QtGui import QPixmap, QDesktopServices, QIcon, QFontMetrics, QImageReader
from qfluentwidgets import (CardWidget, StrongBodyLabel, BodyLabel, CaptionLabel, 
                            TransparentPushButton, FluentIcon, ImageLabel, ScrollArea, MessageBoxBase, SubtitleLabel)

from core.history_manager import history_mgr

class TaskDetailsDialog(MessageBoxBase):
    def __init__(self, task_data, parent=None):
        super().__init__(parent)
        self.titleLabel = SubtitleLabel("Task Details", self)
        self.viewLayout.addWidget(self.titleLabel)
        
        # Content
        self.content = QTextBrowser()
        self.content.setOpenExternalLinks(True)
        self.content.setStyleSheet("background-color: transparent; border: none;")
        
        # Format details
        html = f"""
        <h3>Prompt</h3>
        <p>{task_data['prompt']}</p>
        <hr>
        <p><b>Model:</b> {task_data['model']}</p>
        <p><b>Size:</b> {task_data['image_size']}</p>
        <p><b>Aspect Ratio:</b> {task_data['aspect_ratio']}</p>
        <p><b>Status:</b> {task_data['status']}</p>
        <p><b>Created At:</b> {task_data['created_at']}</p>
        <p><b>Task ID:</b> {task_data['id']}</p>
        """
        if task_data.get('failure_reason'):
            html += f"<p style='color:red'><b>Error:</b> {task_data['failure_reason']}</p>"
            
        self.content.setHtml(html)
        self.content.setFixedHeight(300)
        
        self.viewLayout.addWidget(self.content)
        
        self.yesButton.setText("Close")
        self.cancelButton.hide()
        self.widget.setMinimumWidth(500)

class ClickableLabel(QLabel):
    clicked = Signal()
    def mousePressEvent(self, event):
        self.clicked.emit()

class HistoryItem(CardWidget):
    regenerateRequested = Signal(dict)

    def __init__(self, task_data, parent=None):
        super().__init__(parent)
        self.task_data = task_data
        self.setFixedHeight(120)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        
        # Thumbnail - Use standard QLabel to ensure fixed size works reliably
        self.thumb = QLabel()
        self.thumb.setFixedSize(88, 88)
        self.thumb.setStyleSheet("background-color: #eee; border-radius: 8px; border: 1px solid #ddd;")
        self.thumb.setScaledContents(True)
        
        if task_data["status"] == "succeeded" and task_data["result_path"] and os.path.exists(task_data["result_path"]):
            # Optimized loading using QImageReader
            reader = QImageReader(task_data["result_path"])
            # Scale to a reasonable thumbnail size (e.g. 2x for high DPI)
            reader.setScaledSize(QSize(176, 176))
            image = reader.read()
            
            if not image.isNull():
                self.thumb.setPixmap(QPixmap.fromImage(image))
            
            self.thumb.setCursor(Qt.PointingHandCursor)
            self.thumb.mousePressEvent = self.on_thumb_click
        else:
            self.thumb.setText("No Image")
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
        self.prompt_label.setToolTip("Click to view full details")
        
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
        regen_btn = TransparentPushButton(FluentIcon.SYNC, "Regenerate")
        regen_btn.setToolTip("Run this task again")
        regen_btn.clicked.connect(self.on_regenerate)
        btn_layout.addWidget(regen_btn)

        if task_data["status"] == "succeeded" and task_data["result_path"]:
            open_btn = TransparentPushButton(FluentIcon.FOLDER, "Open Folder")
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
            
from PySide6.QtCore import QUrl

class HistoryPage(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("HistoryPage")
        self.current_page = 1
        self.items_per_page = 5
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Top bar with Refresh
        top_layout = QHBoxLayout()
        top_layout.setContentsMargins(20, 10, 20, 0)
        top_layout.addStretch()
        self.refresh_btn = TransparentPushButton(FluentIcon.SYNC, "Refresh")
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
        
        self.prev_btn = TransparentPushButton(FluentIcon.LEFT_ARROW, "Previous")
        self.prev_btn.clicked.connect(self.prev_page)
        
        self.page_label = StrongBodyLabel("1 / 1")
        
        self.next_btn = TransparentPushButton(FluentIcon.RIGHT_ARROW, "Next")
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

    def prev_page(self):
        if self.current_page > 1:
            self.current_page -= 1
            self.load_history()

    def next_page(self):
        self.current_page += 1
        self.load_history()

    def load_history(self):
        # Clear existing
        for i in range(self.vbox.count()):
            item = self.vbox.itemAt(i)
            if item.widget():
                item.widget().deleteLater()
                
        all_tasks = history_mgr.get_all_tasks()
        total_items = len(all_tasks)
        total_pages = (total_items + self.items_per_page - 1) // self.items_per_page
        if total_pages == 0: total_pages = 1
        
        if self.current_page > total_pages:
            self.current_page = total_pages
        if self.current_page < 1:
            self.current_page = 1
            
        start_idx = (self.current_page - 1) * self.items_per_page
        end_idx = min(start_idx + self.items_per_page, total_items)
        
        current_tasks = all_tasks[start_idx:end_idx]
        
        if not current_tasks:
            self.vbox.addWidget(BodyLabel("No history yet."))
        else:
            for task in current_tasks:
                item = HistoryItem(task)
                item.regenerateRequested.connect(self.on_regenerate_requested)
                self.vbox.addWidget(item)
        
        # Update Pagination Controls
        self.page_label.setText(f"{self.current_page} / {total_pages}")
        self.prev_btn.setEnabled(self.current_page > 1)
        self.next_btn.setEnabled(self.current_page < total_pages)

    def on_regenerate_requested(self, task_data):
        # Signal up to main window
        if self.window():
            self.window().regenerate_task(task_data)
