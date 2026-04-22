from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QFileDialog, QLabel
from qfluentwidgets import (ScrollArea, SettingCardGroup, LineEdit, PushSettingCard, SettingCard, Slider, ComboBox,
                            FluentIcon, InfoBar, InfoBarPosition, PrimaryPushButton, SwitchSettingCard)

from core.config import cfg
from core.i18n import tr, language_items, normalize_language
from core.model_catalog import VIP_MODELS

class SettingsPage(ScrollArea):
    def __init__(self):
        super().__init__()
        self.setObjectName("SettingsPage")
        self.initUI()

    def initUI(self):
        self.setWidgetResizable(True)
        self.setStyleSheet("QScrollArea { border: none; background-color: transparent; }")
        
        self.container = QWidget()
        self.container.setStyleSheet("background-color: transparent;")
        self.setWidget(self.container)
        
        self.layout = QVBoxLayout(self.container)
        self.layout.setContentsMargins(30, 30, 30, 30)
        self.layout.setSpacing(20)

        # General Settings
        self.general_group = SettingCardGroup(tr("settings.general"), self.container)

        self.language_card = SettingCard(
            FluentIcon.GLOBE,
            tr("settings.language.title"),
            tr("settings.language.content"),
            self.general_group
        )
        self.language_combo = ComboBox(self.language_card)
        self.language_code_by_label = {}
        current_language = normalize_language(cfg.get("language", "en"))
        current_label = None
        for code, label in language_items():
            self.language_combo.addItem(label)
            self.language_code_by_label[label] = code
            if code == current_language:
                current_label = label
        if current_label:
            self.language_combo.setCurrentText(current_label)
        self.language_combo.setFixedWidth(150)
        self.language_card.hBoxLayout.addWidget(self.language_combo)
        self.language_card.hBoxLayout.addSpacing(16)
        self.general_group.addSettingCard(self.language_card)
        
        self.retries_card = SettingCard(
            FluentIcon.SYNC,
            tr("settings.retries.title"),
            tr("settings.retries.content"),
            self.general_group
        )
        
        self.retries_label = QLabel(str(cfg.get("max_retries", 5)), self.retries_card)
        self.retries_slider = Slider(Qt.Horizontal, self.retries_card)
        self.retries_slider.setRange(0, 100)
        self.retries_slider.setValue(cfg.get("max_retries", 5))
        
        self.retries_slider.valueChanged.connect(lambda v: self.retries_label.setText(str(v)))
        
        self.retries_card.hBoxLayout.addWidget(self.retries_label)
        self.retries_card.hBoxLayout.addSpacing(10)
        self.retries_card.hBoxLayout.addWidget(self.retries_slider)
        self.retries_card.hBoxLayout.addSpacing(16)
        
        self.general_group.addSettingCard(self.retries_card)

        self.vip_retry_switch = SwitchSettingCard(
            FluentIcon.SYNC,
            tr("settings.vip_retry.title"),
            f"{tr('settings.vip_retry.content')}\n{tr('settings.vip_retry.models', models=', '.join(VIP_MODELS))}",
            parent=self.general_group
        )
        self.vip_retry_switch.setChecked(cfg.get("vip_moderation_auto_retry", False))
        self.general_group.addSettingCard(self.vip_retry_switch)
        
        # History Items Per Page
        self.history_items_card = SettingCard(
            FluentIcon.HISTORY,
            tr("settings.history.title"),
            tr("settings.history.content"),
            self.general_group
        )
        
        self.history_items_label = QLabel(str(cfg.get("history_items_per_page", 5)), self.history_items_card)
        self.history_items_slider = Slider(Qt.Horizontal, self.history_items_card)
        self.history_items_slider.setRange(1, 100)
        self.history_items_slider.setValue(cfg.get("history_items_per_page", 5))
        
        self.history_items_slider.valueChanged.connect(lambda v: self.history_items_label.setText(str(v)))
        
        self.history_items_card.hBoxLayout.addWidget(self.history_items_label)
        self.history_items_card.hBoxLayout.addSpacing(10)
        self.history_items_card.hBoxLayout.addWidget(self.history_items_slider)
        self.history_items_card.hBoxLayout.addSpacing(16)
        
        self.general_group.addSettingCard(self.history_items_card)
        self.layout.addWidget(self.general_group)

        # Text Format Settings
        self.format_group = SettingCardGroup(tr("settings.format"), self.container)
        
        self.format_switch = SwitchSettingCard(
            FluentIcon.EDIT,
            tr("settings.format_enable.title"),
            tr("settings.format_enable.content"),
            parent=self.format_group
        )
        self.format_switch.setChecked(cfg.get("text_format_enabled", False))
        self.format_group.addSettingCard(self.format_switch)
        
        self.font_size_card = SettingCard(
            FluentIcon.FONT,
            tr("settings.font_size.title"),
            tr("settings.font_size.content"),
            self.format_group
        )
        self.font_size_slider = Slider(Qt.Horizontal, self.font_size_card)
        self.font_size_slider.setRange(8, 72)
        self.font_size_slider.setValue(cfg.get("text_font_size", 12))
        
        self.font_size_label = QLabel(str(cfg.get("text_font_size", 12)), self.font_size_card)
        self.font_size_label.setFixedWidth(30)
        
        self.font_size_slider.valueChanged.connect(lambda v: self.font_size_label.setText(str(v)))
        
        self.font_size_card.hBoxLayout.addWidget(self.font_size_label)
        self.font_size_card.hBoxLayout.addSpacing(10)
        self.font_size_card.hBoxLayout.addWidget(self.font_size_slider)
        self.font_size_card.hBoxLayout.addSpacing(16)
        self.format_group.addSettingCard(self.font_size_card)
        
        # Font Family
        self.font_family_card = SettingCard(
            FluentIcon.FONT,
            tr("settings.font_family.title"),
            tr("settings.font_family.content"),
            self.format_group
        )
        self.font_family_combo = ComboBox(self.font_family_card)
        self.font_family_combo.addItems(["Arial", "Courier New", "Times New Roman", "Verdana", "Georgia", "SimSun", "SimHei", "KaiTi"])
        self.font_family_combo.setCurrentText(cfg.get("text_font_family", "Arial"))
        self.font_family_combo.setFixedWidth(150)
        
        self.font_family_card.hBoxLayout.addWidget(self.font_family_combo)
        self.font_family_card.hBoxLayout.addSpacing(16)
        self.format_group.addSettingCard(self.font_family_card)
        
        self.wrap_switch = SwitchSettingCard(
            FluentIcon.ALIGNMENT,
            tr("settings.wrap.title"),
            tr("settings.wrap.content"),
            parent=self.format_group
        )
        self.wrap_switch.setChecked(cfg.get("text_auto_wrap", True))
        self.format_group.addSettingCard(self.wrap_switch)
        self.layout.addWidget(self.format_group)

        # API Settings
        self.api_group = SettingCardGroup(tr("settings.api"), self.container)
        
        # Base URL
        self.url_card = PushSettingCard(
            tr("settings.common.edit"),
            FluentIcon.GLOBE,
            tr("settings.api_url.title"),
            cfg.get("api_base_url"),
            self.api_group
        )
        # We replace the button with a LineEdit for direct editing
        self.url_edit = LineEdit()
        self.url_edit.setText(cfg.get("api_base_url"))
        self.url_edit.setFixedWidth(300)
        self.url_card.hBoxLayout.addWidget(self.url_edit)
        self.url_card.hBoxLayout.addSpacing(16)
        # Remove the default button from PushSettingCard if possible, or just ignore it.
        # Actually, PushSettingCard is designed for a button action. 
        # Let's just use a custom layout or modify it.
        # Simpler: Just use the LineEdit and a Save button at the bottom.
        
        # API Key
        self.key_card = PushSettingCard(
            tr("settings.common.edit"),
            FluentIcon.VPN,
            tr("settings.api_key.title"),
            tr("settings.api_key.content"),
            self.api_group
        )
        self.key_edit = LineEdit()
        self.key_edit.setText(cfg.get("api_key"))
        self.key_edit.setEchoMode(LineEdit.Password)
        self.key_edit.setFixedWidth(300)
        self.key_card.hBoxLayout.addWidget(self.key_edit)
        self.key_card.hBoxLayout.addSpacing(16)

        self.api_group.addSettingCard(self.url_card)
        self.api_group.addSettingCard(self.key_card)
        self.layout.addWidget(self.api_group)

        # Output Settings
        self.output_group = SettingCardGroup(tr("settings.output"), self.container)
        
        self.path_card = PushSettingCard(
            tr("settings.output.choose"),
            FluentIcon.FOLDER,
            tr("settings.output.title"),
            cfg.get("output_folder"),
            self.output_group
        )
        self.path_card.clicked.connect(self.choose_folder)
        
        self.output_group.addSettingCard(self.path_card)
        self.layout.addWidget(self.output_group)

        # Save Button
        self.save_btn = PrimaryPushButton(tr("settings.save"))
        self.save_btn.clicked.connect(self.save_settings)
        self.save_btn.setFixedWidth(200)
        self.layout.addWidget(self.save_btn, 0, Qt.AlignRight)
        
        self.layout.addStretch()

    def resizeEvent(self, event):
        """Dynamically adjust slider widths to 60% of parent width"""
        super().resizeEvent(event)
        parent_width = self.width()
        if parent_width > 0:
            slider_width = int(parent_width * 0.6)
            self.retries_slider.setFixedWidth(max(slider_width, 100))
            self.font_size_slider.setFixedWidth(max(slider_width, 100))
            self.history_items_slider.setFixedWidth(max(slider_width, 100))

    def choose_folder(self):
        folder = QFileDialog.getExistingDirectory(self, tr("settings.dialog.select_folder"), cfg.get("output_folder"))
        if folder:
            self.path_card.setContent(folder)
            cfg.set("output_folder", folder)

    def save_settings(self):
        url = self.url_edit.text().strip()
        key = self.key_edit.text().strip()
        selected_language_label = self.language_combo.currentText()
        new_language = self.language_code_by_label.get(selected_language_label, "en")
        old_language = normalize_language(cfg.get("language", "en"))
        language_changed = new_language != old_language
        
        cfg.set("api_base_url", url)
        cfg.set("api_key", key)
        cfg.set("language", new_language)
        cfg.set("max_retries", self.retries_slider.value())
        cfg.set("vip_moderation_auto_retry", self.vip_retry_switch.isChecked())
        cfg.set("history_items_per_page", self.history_items_slider.value())
        cfg.set("text_format_enabled", self.format_switch.isChecked())
        cfg.set("text_font_size", self.font_size_slider.value())
        cfg.set("text_font_family", self.font_family_combo.currentText())
        cfg.set("text_auto_wrap", self.wrap_switch.isChecked())
        
        # Also save current generator settings if available
        try:
            main_window = self.window()
            if hasattr(main_window, 'generator_interface'):
                gen_page = main_window.generator_interface
                # Save current model and its parameters
                model = gen_page.model_combo.currentText()
                cfg.set("last_model", model)
                
                if model.startswith("nano-banana"):
                    cfg.set("nano_banana_aspect_ratio", gen_page.ratio_combo.currentText())
                    cfg.set("nano_banana_image_size", gen_page.size_combo.currentText())
                elif gen_page._is_completion_model(model):
                    cfg.set("gpt_image_size", gen_page.gpt_size_combo.currentText())
                
                # Save shared parameters
                cfg.set("auto_retry_on_failure", gen_page.auto_retry_cb.isChecked())
                cfg.set("parallel_tasks", gen_page.parallel_slider.value())
        except:
            pass
        
        # Apply text formatting to generator page
        try:
            main_window = self.window()
            if hasattr(main_window, 'generator_interface'):
                main_window.generator_interface.update_text_formatting()
        except:
            pass
        
        InfoBar.success(
            title=tr("settings.saved_title"),
            content=tr("settings.saved_content_restart") if language_changed else tr("settings.saved_content"),
            parent=self,
            position=InfoBarPosition.TOP_RIGHT
        )
