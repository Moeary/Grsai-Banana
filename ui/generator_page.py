import os
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSizePolicy, QApplication
from qfluentwidgets import (CardWidget, PrimaryPushButton, ComboBox, CaptionLabel, 
                            InfoBar, InfoBarPosition, SegmentedWidget, CheckBox, Slider,
                            TransparentToolButton, FluentIcon, StrongBodyLabel, BodyLabel, isDarkTheme, qconfig)

from core.config import cfg
from core.i18n import tr
from core.model_catalog import (
    TAB_BANANA_1,
    TAB_BANANA_PRO,
    TAB_GPT_IMAGE,
    TAB_MODELS,
    NANO_IMAGE_SIZE_OPTIONS,
    VIP_MODELS,
    LEGACY_IMAGE_MODEL_ALIASES,
)
from core.task_manager import task_manager
from ui.components.prompt_widget import PromptWidget
from ui.components.image_drop_area import ImageDropArea
from ui.components.task_widget import TaskWidget, TaskListWidget

class GeneratorPage(QWidget):
    TAB_MODELS = TAB_MODELS
    NANO_IMAGE_SIZE_OPTIONS = NANO_IMAGE_SIZE_OPTIONS
    VIP_MODELS = set(VIP_MODELS)
    LEGACY_MODEL_ALIASES = LEGACY_IMAGE_MODEL_ALIASES

    def __init__(self):
        super().__init__()
        self.setObjectName("GeneratorPage")
        self.task_counter = 0
        self.current_tab_key = TAB_BANANA_1
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
        self.model_tabs.addItem(TAB_BANANA_1, tr("generator.tab.banana_1"))
        self.model_tabs.addItem(TAB_BANANA_PRO, tr("generator.tab.banana_pro"))
        self.model_tabs.addItem(TAB_GPT_IMAGE, tr("generator.tab.gpt_image"))
        
        # Load last selected tab or default
        last_tab = self._normalize_tab_key(cfg.get("last_tab", TAB_BANANA_1))
        if last_tab in [TAB_BANANA_1, TAB_BANANA_PRO, TAB_GPT_IMAGE]:
            self.model_tabs.setCurrentItem(last_tab)
        else:
            self.model_tabs.setCurrentItem(TAB_BANANA_1)
            
        self.model_tabs.currentItemChanged.connect(self.on_tab_changed)
        settings_layout_v.addWidget(self.model_tabs)
        
        # 2. Settings Card
        self.settings_card = CardWidget()
        # Unify card background color
        self.update_card_style(self.settings_card)
        qconfig.themeChanged.connect(lambda: self.update_card_style(self.settings_card))
        settings_inner = QVBoxLayout(self.settings_card)
        
        # Model Selector (Specific to tab)
        self.model_caption = CaptionLabel(tr("generator.model"))
        settings_inner.addWidget(self.model_caption)
        self.model_combo = ComboBox()
        self.model_combo.currentTextChanged.connect(self.on_model_changed)
        settings_inner.addWidget(self.model_combo)

        # Aspect Ratio (Banana)
        self.ratio_label = CaptionLabel(tr("generator.aspect_ratio"))
        settings_inner.addWidget(self.ratio_label)
        self.ratio_combo = ComboBox()
        self.ratio_combo.addItems(["auto", "1:1", "16:9", "9:16", "4:3", "3:4", "3:2", "2:3", "5:4", "4:5", "21:9"])
        self.ratio_combo.setCurrentText(cfg.get("nano_banana_aspect_ratio", "auto"))
        settings_inner.addWidget(self.ratio_combo)

        # Image Size (Banana Pro)
        self.size_label = CaptionLabel(tr("generator.image_size"))
        settings_inner.addWidget(self.size_label)
        self.size_combo = ComboBox()
        self.size_combo.addItems(["1K", "2K", "4K"])
        self.size_combo.setCurrentText(cfg.get("nano_banana_image_size", "1K"))
        settings_inner.addWidget(self.size_combo)
        
        # Variants (GPT)
        self.variants_label = CaptionLabel(tr("generator.variants"))
        settings_inner.addWidget(self.variants_label)
        self.variants_combo = ComboBox()
        self.variants_combo.addItems(["1", "2"])
        self.variants_combo.setCurrentText("1")
        settings_inner.addWidget(self.variants_combo)

        # Size (GPT)
        self.gpt_size_label = CaptionLabel(tr("generator.gpt_size"))
        settings_inner.addWidget(self.gpt_size_label)
        self.gpt_size_combo = ComboBox()
        self.gpt_size_combo.addItems(["auto", "1:1", "3:2", "2:3"])
        self.gpt_size_combo.setCurrentText(cfg.get("gpt_image_size", "auto"))
        settings_inner.addWidget(self.gpt_size_combo)
        
        # Auto Retry and Parallel Tasks
        retry_parallel_layout = QHBoxLayout()
        
        self.auto_retry_cb = CheckBox(tr("generator.auto_retry"))
        self.auto_retry_cb.setChecked(cfg.get("auto_retry_on_failure", False))
        retry_parallel_layout.addWidget(self.auto_retry_cb)
        
        retry_parallel_layout.addStretch()
        
        self.parallel_label = BodyLabel(tr("generator.parallel_tasks"))
        parallel_label = self.parallel_label
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

        self.auto_retry_hint = CaptionLabel("")
        self.auto_retry_hint.setWordWrap(True)
        self.auto_retry_hint.hide()
        settings_inner.addWidget(self.auto_retry_hint)

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
        self.ref_images_label = StrongBodyLabel(tr("generator.reference_images"))
        img_header_layout.addWidget(self.ref_images_label)
        img_header_layout.addStretch()
        
        img_paste_btn = TransparentToolButton(FluentIcon.PASTE)
        img_paste_btn.setToolTip(tr("drop.tooltip.paste"))
        img_paste_btn.clicked.connect(self.on_image_paste)
        img_header_layout.addWidget(img_paste_btn)
        
        img_clear_btn = TransparentToolButton(FluentIcon.DELETE)
        img_clear_btn.setToolTip(tr("drop.tooltip.clear"))
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
        self.gen_btn = PrimaryPushButton(tr("generator.generate"))
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
        self.task_list_tabs_spacer.addItem("task_list", tr("generator.task_list"))
        self.task_list_tabs_spacer.setCurrentItem("task_list")
        self.task_list_tabs_spacer.setEnabled(False)
        right_layout.addWidget(self.task_list_tabs_spacer)
        
        self.task_list_widget = TaskListWidget()
        right_layout.addWidget(self.task_list_widget, 1)
        
        main_layout.addWidget(right_panel, 1)

        # Initialize state
        self.on_tab_changed(self.model_tabs.currentItem())

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

    def _is_nano_model(self, model_name):
        return model_name.startswith("nano-banana")

    def _is_completion_model(self, model_name):
        normalized_model = self.LEGACY_MODEL_ALIASES.get(model_name, model_name)
        return normalized_model.startswith("gpt-image")

    def get_tab_for_model(self, model_name):
        model_name = self.LEGACY_MODEL_ALIASES.get(model_name, model_name)
        for tab_name, models in self.TAB_MODELS.items():
            if model_name in models:
                return tab_name
        if model_name.startswith("nano-banana-pro"):
            return TAB_BANANA_PRO
        if model_name.startswith("nano-banana"):
            return TAB_BANANA_1
        return TAB_GPT_IMAGE

    def _set_combo_items(self, combo, items, preferred=None):
        combo.blockSignals(True)
        combo.clear()
        combo.addItems(items)
        if preferred in items:
            combo.setCurrentText(preferred)
        elif items:
            combo.setCurrentText(items[0])
        combo.blockSignals(False)

    def _normalize_tab_key(self, tab_key_or_text):
        if tab_key_or_text in self.TAB_MODELS:
            return tab_key_or_text

        tab_display_map = {
            tr("generator.tab.banana_1"): TAB_BANANA_1,
            tr("generator.tab.banana_pro"): TAB_BANANA_PRO,
            tr("generator.tab.gpt_image"): TAB_GPT_IMAGE,
            "Banana 1": TAB_BANANA_1,
            "Banana Pro": TAB_BANANA_PRO,
            "GPT Image": TAB_GPT_IMAGE,
        }
        return tab_display_map.get(tab_key_or_text, TAB_BANANA_1)

    def _update_auto_retry_hint(self, model_name):
        if model_name in self.VIP_MODELS:
            if cfg.get("vip_moderation_auto_retry", False):
                self.auto_retry_hint.setText(tr("generator.vip_hint_enabled"))
            else:
                self.auto_retry_hint.setText(tr("generator.vip_hint_disabled"))
            self.auto_retry_hint.show()
        else:
            self.auto_retry_hint.hide()

    def on_tab_changed(self, tab_name):
        if hasattr(tab_name, "routeKey"):
            route_key = tab_name.routeKey
            tab_name = route_key() if callable(route_key) else route_key
        elif hasattr(tab_name, "text"):
            text = tab_name.text
            tab_name = text() if callable(text) else text
        elif not isinstance(tab_name, str):
            tab_name = str(tab_name)

        tab_name = self._normalize_tab_key(tab_name)

        self.current_tab_key = tab_name
        cfg.set("last_tab", tab_name)
        
        self.model_combo.blockSignals(True)
        self.model_combo.clear()

        self.model_combo.addItems(self.TAB_MODELS.get(tab_name, []))
            
        # Restore last selected model for this tab if possible, or default
        last_model = cfg.get(f"last_model_tab_{tab_name}", self.model_combo.itemText(0))
        last_model = self.LEGACY_MODEL_ALIASES.get(last_model, last_model)
        if self.model_combo.findText(last_model) >= 0:
            self.model_combo.setCurrentText(last_model)
        
        self.model_combo.blockSignals(False)
        self.on_model_changed(self.model_combo.currentText())

    def on_model_changed(self, model_name):
        if not model_name: return
        model_name = self.LEGACY_MODEL_ALIASES.get(model_name, model_name)
        
        tab_name = getattr(self, "current_tab_key", TAB_BANANA_1)
        cfg.set(f"last_model_tab_{tab_name}", model_name)

        is_nano = self._is_nano_model(model_name)
        is_completion = self._is_completion_model(model_name)
        size_options = self.NANO_IMAGE_SIZE_OPTIONS.get(model_name)

        self.ratio_label.setVisible(is_nano)
        self.ratio_combo.setVisible(is_nano)

        show_size = bool(size_options)
        self.size_label.setVisible(show_size)
        self.size_combo.setVisible(show_size)
        if show_size:
            selected_size = cfg.get("nano_banana_image_size", "1K")
            if selected_size not in size_options:
                selected_size = size_options[0]
            self._set_combo_items(self.size_combo, size_options, selected_size)

        self.variants_label.setVisible(is_completion)
        self.variants_combo.setVisible(is_completion)

        self.gpt_size_label.setVisible(is_completion)
        self.gpt_size_combo.setVisible(is_completion)

        self._update_auto_retry_hint(model_name)

    def update_text_formatting(self):
        self.prompt_widget.update_text_formatting()

    def on_generate(self):
        prompt = self.prompt_widget.get_prompt()
        if not prompt:
            InfoBar.warning(title=tr("common.warning"), content=tr("generator.enter_prompt_warning"), parent=self, position=InfoBarPosition.TOP_RIGHT)
            return

        model = self.model_combo.currentText()
        
        # Get params based on active model
        ratio = "auto"
        size = "1K"
        variants = 1

        if self._is_nano_model(model):
            ratio = self.ratio_combo.currentText()
            cfg.set("nano_banana_aspect_ratio", ratio)

            if model in self.NANO_IMAGE_SIZE_OPTIONS:
                size = self.size_combo.currentText()
                cfg.set("nano_banana_image_size", size)
        elif self._is_completion_model(model):
            variants = int(self.variants_combo.currentText())
            size = self.gpt_size_combo.currentText()
            cfg.set("gpt_image_size", size)

        parallel_count = self.parallel_slider.value()
        
        # For GPT Image variants, warn about parallel execution
        if self._is_completion_model(model) and variants > 1 and parallel_count > 1:
            InfoBar.warning(
                title=tr("common.note"), 
                content=tr("generator.parallel_note", variants=variants),
                parent=self, 
                position=InfoBarPosition.TOP_RIGHT
            )
            parallel_count = 1
        
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
        
        # Show variants info for GPT Image models
        variants = params.get("variants", 1)
        if variants > 1:
            task_widget.set_variants_info(variants)
        
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
            task_widget.set_failed(result, msg)

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
