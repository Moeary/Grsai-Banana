import os
from datetime import datetime
from PySide6.QtCore import Qt, QSize
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSizePolicy, QScrollArea, QApplication)
from qfluentwidgets import (CardWidget, PrimaryPushButton, ComboBox, CaptionLabel, 
                            InfoBar, InfoBarPosition, SegmentedWidget, CheckBox, Slider,
                            TransparentToolButton, FluentIcon, StrongBodyLabel, BodyLabel, isDarkTheme, qconfig)

from core.config import cfg
from core.task_manager import task_manager
from ui.components.prompt_widget import PromptWidget
from ui.components.image_drop_area import ImageDropArea
from ui.components.task_widget import TaskWidget, TaskListWidget

class GeneratorPage(QWidget):
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
        
        # --- Top Section: Tabs & Settings ---
        settings_container = QWidget()
        settings_layout_v = QVBoxLayout(settings_container)
        settings_layout_v.setContentsMargins(0, 0, 0, 0)
        settings_layout_v.setSpacing(10)
        
        # 1. Tabs
        self.model_tabs = SegmentedWidget()
        self.model_tabs.addItem("Banana 1", "Banana 1")
        self.model_tabs.addItem("Banana Pro", "Banana Pro")
        self.model_tabs.addItem("GPT Image", "GPT Image")
        
        # Load last selected tab or default
        last_tab = cfg.get("last_tab", "Banana 1")
        if last_tab in ["Banana 1", "Banana Pro", "GPT Image"]:
            self.model_tabs.setCurrentItem(last_tab)
        else:
            self.model_tabs.setCurrentItem("Banana 1")
            
        self.model_tabs.currentItemChanged.connect(self.on_tab_changed)
        settings_layout_v.addWidget(self.model_tabs)
        
        # 2. Settings Card
        self.settings_card = CardWidget()
        # Unify card background color
        self.update_card_style(self.settings_card)
        qconfig.themeChanged.connect(lambda: self.update_card_style(self.settings_card))
        settings_inner = QVBoxLayout(self.settings_card)
        
        # Model Selector (Specific to tab)
        settings_inner.addWidget(CaptionLabel("Model"))
        self.model_combo = ComboBox()
        self.model_combo.currentTextChanged.connect(self.on_model_changed)
        settings_inner.addWidget(self.model_combo)

        # Aspect Ratio (Banana)
        self.ratio_label = CaptionLabel("Aspect Ratio")
        settings_inner.addWidget(self.ratio_label)
        self.ratio_combo = ComboBox()
        self.ratio_combo.addItems(["auto", "1:1", "16:9", "9:16", "4:3", "3:4", "3:2", "2:3", "5:4", "4:5", "21:9"])
        self.ratio_combo.setCurrentText(cfg.get("nano_banana_aspect_ratio", "auto"))
        settings_inner.addWidget(self.ratio_combo)

        # Image Size (Banana Pro)
        self.size_label = CaptionLabel("Image Size")
        settings_inner.addWidget(self.size_label)
        self.size_combo = ComboBox()
        self.size_combo.addItems(["1K", "2K", "4K"])
        self.size_combo.setCurrentText(cfg.get("nano_banana_image_size", "1K"))
        settings_inner.addWidget(self.size_combo)
        
        # Variants (GPT)
        self.variants_label = CaptionLabel("Variants")
        settings_inner.addWidget(self.variants_label)
        self.variants_combo = ComboBox()
        self.variants_combo.addItems(["1", "2"])
        self.variants_combo.setCurrentText("1")
        settings_inner.addWidget(self.variants_combo)

        # Size (GPT)
        self.gpt_size_label = CaptionLabel("Image Size (GPT/Sora)")
        settings_inner.addWidget(self.gpt_size_label)
        self.gpt_size_combo = ComboBox()
        self.gpt_size_combo.addItems(["auto", "1:1", "3:2", "2:3"])
        self.gpt_size_combo.setCurrentText(cfg.get("gpt_image_size", "auto"))
        settings_inner.addWidget(self.gpt_size_combo)
        
        # Auto Retry and Parallel Tasks
        retry_parallel_layout = QHBoxLayout()
        
        self.auto_retry_cb = CheckBox("Auto Retry on Failure")
        self.auto_retry_cb.setChecked(cfg.get("auto_retry_on_failure", False))
        retry_parallel_layout.addWidget(self.auto_retry_cb)
        
        retry_parallel_layout.addStretch()
        
        parallel_label = BodyLabel("Parallel Tasks (1-10):")
        retry_parallel_layout.addWidget(parallel_label)
        
        self.parallel_slider = Slider(Qt.Horizontal)
        self.parallel_slider.setMinimum(1)
        self.parallel_slider.setMaximum(10)
        self.parallel_slider.setValue(cfg.get("parallel_tasks", 1))
        self.parallel_slider.setFixedWidth(200)
        self.parallel_slider.setTickPosition(Slider.TicksBelow)
        self.parallel_slider.setTickInterval(1)
        retry_parallel_layout.addWidget(self.parallel_slider)
        
        self.parallel_value_label = QLabel(str(cfg.get("parallel_tasks", 1)))
        self.parallel_value_label.setFixedWidth(24)
        self.update_parallel_value_label_color()
        self.parallel_slider.valueChanged.connect(lambda v: self.parallel_value_label.setText(str(v)))
        retry_parallel_layout.addWidget(self.parallel_value_label)
        
        settings_inner.addLayout(retry_parallel_layout)
        settings_layout_v.addWidget(self.settings_card)
        
        left_layout.addWidget(settings_container)
        
        # --- Middle Section: Images & Prompt ---
        middle_split = QWidget()
        middle_layout = QHBoxLayout(middle_split)
        middle_layout.setContentsMargins(0, 0, 0, 0)
        middle_layout.setSpacing(15)
        
        # Image Drop Area with Header
        img_container = QWidget()
        img_container_layout = QVBoxLayout(img_container)
        img_container_layout.setContentsMargins(0, 0, 0, 0)
        img_container_layout.setSpacing(5)
        
        # Image Drop Area Header
        img_header_layout = QHBoxLayout()
        img_header_layout.setContentsMargins(0, 0, 0, 0)
        img_header_layout.addWidget(StrongBodyLabel("Reference Images"))
        img_header_layout.addStretch()
        
        img_paste_btn = TransparentToolButton(FluentIcon.PASTE)
        img_paste_btn.setToolTip("Paste from clipboard")
        img_paste_btn.clicked.connect(self.on_image_paste)
        img_header_layout.addWidget(img_paste_btn)
        
        img_clear_btn = TransparentToolButton(FluentIcon.DELETE)
        img_clear_btn.setToolTip("Clear all images")
        img_clear_btn.clicked.connect(self.on_image_clear)
        img_header_layout.addWidget(img_clear_btn)
        
        img_container_layout.addLayout(img_header_layout)
        
        # Image Drop Area
        self.drop_area = ImageDropArea()
        self.drop_area.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        img_container_layout.addWidget(self.drop_area)
        
        middle_layout.addWidget(img_container, 1)
        
        # Prompt Widget
        self.prompt_widget = PromptWidget()
        self.prompt_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        middle_layout.addWidget(self.prompt_widget, 1)
        
        left_layout.addWidget(middle_split, 1)
        
        # --- Bottom Section: Generate Button ---
        self.gen_btn = PrimaryPushButton("Generate Image")
        self.gen_btn.clicked.connect(self.on_generate)
        self.gen_btn.setFixedHeight(45)
        left_layout.addWidget(self.gen_btn)
        
        main_layout.addWidget(left_panel, 2)

        # Right Side (1/3 width) - Task List
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(10)
        
        # Add a dummy widget to match the tabs spacing
        self.task_list_tabs_spacer = SegmentedWidget()
        self.task_list_tabs_spacer.addItem("Task List", "Task List")
        self.task_list_tabs_spacer.setCurrentItem("Task List")
        self.task_list_tabs_spacer.setEnabled(False)
        right_layout.addWidget(self.task_list_tabs_spacer)
        
        self.task_list_widget = TaskListWidget()
        right_layout.addWidget(self.task_list_widget, 1)
        
        main_layout.addWidget(right_panel, 1)

        # Initialize state
        self.on_tab_changed(self.model_tabs.currentItem().text())

    def keyPressEvent(self, event):
        if event.modifiers() == Qt.ControlModifier and event.key() == Qt.Key_V:
            clipboard = QApplication.clipboard()
            mime_data = clipboard.mimeData()
            if mime_data.hasImage() or mime_data.hasUrls():
                self.drop_area.paste_from_clipboard()

    def update_parallel_value_label_color(self):
        """Update the color of the parallel value label based on theme"""
        if isDarkTheme():
            self.parallel_value_label.setStyleSheet("color: #ffffff;")
        else:
            self.parallel_value_label.setStyleSheet("color: #000000;")

    def update_card_style(self, card_widget):
        """Unify card background color for both light and dark themes"""
        if isDarkTheme():
            bg_color = "rgba(255, 255, 255, 0.06)"
        else:
            bg_color = "rgb(255, 255, 255)"
        card_widget.setStyleSheet(f"CardWidget {{ background-color: {bg_color}; }}")

    def on_tab_changed(self, tab_name):
        cfg.set("last_tab", tab_name)
        
        self.model_combo.blockSignals(True)
        self.model_combo.clear()
        
        if tab_name == "Banana 1":
            self.model_combo.addItems(["nano-banana-fast", "nano-banana"])
        elif tab_name == "Banana Pro":
            self.model_combo.addItems(["nano-banana-pro", "nano-banana-pro-vt"])
        elif tab_name == "GPT Image":
            self.model_combo.addItems(["gpt-image-1.5", "sora-image"])
            
        # Restore last selected model for this tab if possible, or default
        last_model = cfg.get(f"last_model_{tab_name}", self.model_combo.itemText(0))
        if self.model_combo.findText(last_model) >= 0:
            self.model_combo.setCurrentText(last_model)
        
        self.model_combo.blockSignals(False)
        self.on_model_changed(self.model_combo.currentText())

    def on_model_changed(self, model_name):
        if not model_name: return
        
        tab_name = self.model_tabs.currentItem().text()
        cfg.set(f"last_model_{tab_name}", model_name)
        
        # Visibility Logic
        is_banana = tab_name in ["Banana 1", "Banana 1"] # Typo fix: Banana 1 or Banana Pro
        is_banana = tab_name in ["Banana 1", "Banana Pro"]
        is_gpt = tab_name == "GPT Image"
        is_pro = tab_name == "Banana Pro"
        
        self.ratio_label.setVisible(is_banana)
        self.ratio_combo.setVisible(is_banana)
        
        self.size_label.setVisible(is_pro)
        self.size_combo.setVisible(is_pro)
        
        self.variants_label.setVisible(is_gpt)
        self.variants_combo.setVisible(is_gpt)
        
        # GPT Image 1.5 specific
        is_gpt_1_5 = model_name == "gpt-image-1.5"
        self.gpt_size_label.setVisible(is_gpt_1_5)
        self.gpt_size_combo.setVisible(is_gpt_1_5)

    def update_text_formatting(self):
        self.prompt_widget.update_text_formatting()

    def on_generate(self):
        prompt = self.prompt_widget.get_prompt()
        if not prompt:
            InfoBar.warning(title="Warning", content="Please enter a prompt.", parent=self, position=InfoBarPosition.TOP_RIGHT)
            return

        model = self.model_combo.currentText()
        tab_name = self.model_tabs.currentItem().text()
        
        # Get params based on active tab/model
        ratio = "auto"
        size = "1K"
        variants = 1
        
        if tab_name in ["Banana 1", "Banana Pro"]:
            ratio = self.ratio_combo.currentText()
            cfg.set("nano_banana_aspect_ratio", ratio)
            if tab_name == "Banana Pro":
                size = self.size_combo.currentText()
                cfg.set("nano_banana_image_size", size)
        elif tab_name == "GPT Image":
            variants = int(self.variants_combo.currentText())
            if model == "gpt-image-1.5":
                size = self.gpt_size_combo.currentText()
                cfg.set("gpt_image_size", size)

        parallel_count = self.parallel_slider.value()
        
        cfg.set("auto_retry_on_failure", self.auto_retry_cb.isChecked())
        cfg.set("parallel_tasks", parallel_count)
        
        ref_urls = []
        for img_path in self.drop_area.image_paths:
            if os.path.isfile(img_path):
                ref_urls.append(img_path)

        params = {
            "model": model,
            "ratio": ratio,
            "size": size,
            "ref_urls": ref_urls,
            "variants": variants
        }
        
        for _ in range(parallel_count):
            self.create_task(prompt, params)

    def create_task(self, prompt, params):
        self.task_counter += 1
        task_widget = TaskWidget(self.task_counter, prompt, params)
        task_widget.auto_retry = self.auto_retry_cb.isChecked()
        task_widget.retry_requested.connect(self.retry_task)
        task_widget.regenerate_requested.connect(self.regenerate_task)
        
        self.task_list_widget.add_task(task_widget)
        self.start_worker(task_widget)

    def start_worker(self, task_widget):
        try:
            variants = task_widget.params.get("variants", 1)
            worker = task_manager.create_worker(
                task_widget.prompt, 
                task_widget.params["model"], 
                task_widget.params["ratio"], 
                task_widget.params["size"], 
                task_widget.params["ref_urls"],
                variants=variants
            )
            
            task_widget.progress_ring.show()
            task_widget.progress_ring.setValue(0)
            task_widget.status_label.setText(f"Attempt {task_widget.attempt_count + 1}: Starting...")
            
            worker.progress_signal.connect(task_widget.update_progress)
            worker.finished_signal.connect(lambda s, r, m: self.on_worker_finished(task_widget, s, r, m))
            worker.finished.connect(lambda: self.cleanup_worker(task_widget))
            
            task_manager.register_worker(task_widget, worker)
            worker.start()
        except Exception as e:
            print(f"[GeneratorPage] Error in start_worker: {e}")

    def on_worker_finished(self, task_widget, success, result, msg):
        if success:
            task_widget.set_success(result)
        else:
            task_widget.set_failed(msg)

    def cleanup_worker(self, task_widget):
        task_manager.unregister_worker(task_widget)

    def retry_task(self, task_widget):
        self.start_worker(task_widget)
    
    def regenerate_task(self, task_widget):
        self.create_task(task_widget.prompt, task_widget.params.copy())
    
    def on_image_paste(self):
        self.drop_area.paste_from_clipboard()
    
    def on_image_clear(self):
        self.drop_area.clear_images()
    
    def stop_all_workers(self):
        task_manager.stop_all_workers()
