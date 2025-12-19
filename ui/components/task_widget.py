from PySide6.QtCore import Qt, Signal, QUrl, QSize, QTimer
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFrame, QStackedWidget, QScrollArea)
from PySide6.QtGui import QPixmap, QIcon, QDesktopServices
from qfluentwidgets import (StrongBodyLabel, BodyLabel, TransparentToolButton, ProgressRing, FluentIcon, isDarkTheme, qconfig)

from core.config import cfg

class TaskWidget(QFrame):
    retry_requested = Signal(object)
    regenerate_requested = Signal(object)

    def __init__(self, index, prompt, params, parent=None):
        super().__init__(parent)
        self.index = index
        self.prompt = prompt
        self.params = params
        self.retry_count = 0
        self.attempt_count = 0
        self.max_retries = cfg.get("max_retries", 5)
        self.auto_retry = False
        self.retry_timer = QTimer()
        self.retry_timer.setSingleShot(True)
        self.retry_timer.timeout.connect(self.perform_auto_retry)
        self.status_text = "Pending"
        self.result_path = None
        self.current_status = "normal"
        
        self.setFixedHeight(120)
        self.update_style()
        qconfig.themeChanged.connect(lambda: self.update_style(self.current_status))
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(15)
        
        self.index_label = StrongBodyLabel(f"#{index}")
        self.index_label.setFixedWidth(40)
        layout.addWidget(self.index_label)
        
        self.status_label = BodyLabel("Attempt: 1")
        layout.addWidget(self.status_label, 1)
        
        self.status_stack = QStackedWidget()
        self.status_stack.setFixedSize(50, 50)
        
        self.progress_ring = ProgressRing()
        self.progress_ring.setFixedSize(50, 50)
        self.progress_ring.setTextVisible(True)
        self.status_stack.addWidget(self.progress_ring)
        
        self.result_btn = TransparentToolButton(FluentIcon.PHOTO, self)
        self.result_btn.setFixedSize(50, 50)
        self.result_btn.setIconSize(QSize(40, 40))
        self.result_btn.clicked.connect(self.open_image)
        self.status_stack.addWidget(self.result_btn)
        
        self.retry_btn = TransparentToolButton(FluentIcon.SYNC, self)
        self.retry_btn.setFixedSize(50, 50)
        self.retry_btn.setIconSize(QSize(30, 30))
        self.retry_btn.setToolTip("Retry")
        self.retry_btn.clicked.connect(self.on_retry_click)
        self.status_stack.addWidget(self.retry_btn)
        
        self.status_stack.setCurrentIndex(0)
        layout.addWidget(self.status_stack)

    def update_style(self, status="normal"):
        # Base style
        if isDarkTheme():
            bg_color = "rgba(255, 255, 255, 0.05)"
        else:
            bg_color = "rgba(0, 0, 0, 0.1)"
            
        border = "1px solid #e0e0e0"
        
        if status == "success":
            border = "1px solid #90EE90"
            if isDarkTheme():
                bg_color = "rgba(255, 255, 255, 0.1)"
            else:
                bg_color = "rgba(0, 255, 0, 0.1)"
        elif status == "failed":
            border = "1px solid #FFB6C1"
            if isDarkTheme():
                bg_color = "rgba(255, 255, 255, 0.1)"
            else:
                bg_color = "rgba(255, 0, 0, 0.1)"
                
        self.current_status = status
        self.setStyleSheet(f"TaskWidget {{ border: {border}; border-radius: 8px; background-color: {bg_color}; }}")

    def update_progress(self, value, status):
        self.status_stack.setCurrentIndex(0)
        self.progress_ring.setValue(value)
        self.status_text = status
        self.status_label.setText(f"Attempt {self.attempt_count + 1}: {status}")
        self.progress_ring.setToolTip(f"Status: {status}")
        
    def set_success(self, filepath):
        self.result_path = filepath
        self.status_stack.setCurrentIndex(1)
        
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
        
        self.result_btn.setContextMenuPolicy(Qt.CustomContextMenu)
        self.result_btn.customContextMenuRequested.connect(self.show_result_menu)
            
        self.update_style("success")

    def set_failed(self, reason):
        try:
            self.status_stack.setCurrentIndex(2)
            self.retry_btn.setToolTip(f"Failed: {reason}. Click to retry.")
            self.status_label.setText(f"✗ Failed: {reason}")
            self.update_style("failed")
            
            if self.auto_retry and self.retry_count < self.max_retries:
                print(f"[TaskWidget] Auto-retrying... ({self.retry_count + 1}/{self.max_retries})")
                self.retry_count += 1
                self.attempt_count += 1
                self.retry_timer.start(1000)
        except Exception as e:
            print(f"[TaskWidget] Error in set_failed: {e}")
    
    def perform_auto_retry(self):
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

    def show_result_menu(self, pos):
        from PySide6.QtWidgets import QMenu
        menu = QMenu()
        regenerate_action = menu.addAction("Regenerate New Image")
        regenerate_action.triggered.connect(self.regenerate)
        menu.exec(self.result_btn.mapToGlobal(pos))

    def regenerate(self):
        self.regenerate_requested.emit(self)

class TaskListWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        self.task_scroll = QScrollArea()
        self.task_scroll.setWidgetResizable(True)
        # Add gray background to the scroll area
        self.update_style()
        qconfig.themeChanged.connect(self.update_style)
        
        self.task_container = QWidget()
        self.task_container.setStyleSheet("background: transparent;")
        self.task_layout = QVBoxLayout(self.task_container)
        self.task_layout.setAlignment(Qt.AlignTop)
        self.task_layout.setSpacing(10)
        
        self.task_scroll.setWidget(self.task_container)
        layout.addWidget(self.task_scroll)

    def update_style(self):
        if isDarkTheme():
            bg_color = "rgba(255, 255, 255, 0.06)"
            border_color = "rgba(255, 255, 255, 0.1)"
        else:
            bg_color = "rgb(255, 255, 255)"
            border_color = "rgba(0, 0, 0, 0.12)"
            
        self.task_scroll.setStyleSheet(f"""
            QScrollArea {{
                background-color: {bg_color};
                border: 1px solid {border_color};
                border-radius: 8px;
            }}
            QWidget#qt_scrollarea_viewport {{
                background-color: transparent;
            }}
        """)

    def add_task(self, task_widget):
        self.task_layout.insertWidget(0, task_widget)
