from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QFileDialog, QLabel, QSpinBox
from qfluentwidgets import (ScrollArea, SettingCardGroup, LineEdit, PushSettingCard, SettingCard, Slider,
                            FluentIcon, InfoBar, InfoBarPosition, PrimaryPushButton, SwitchSettingCard)

from core.config import cfg

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
        self.general_group = SettingCardGroup("General Configuration", self.container)
        
        self.retries_card = SettingCard(
            FluentIcon.SYNC,
            "Max Retries",
            "Maximum number of auto-retries for failed tasks",
            self.general_group
        )
        
        self.retries_label = QLabel(str(cfg.get("max_retries", 5)), self.retries_card)
        self.retries_slider = Slider(Qt.Horizontal, self.retries_card)
        self.retries_slider.setRange(0, 100)
        self.retries_slider.setValue(cfg.get("max_retries", 5))
        self.retries_slider.setFixedWidth(150)
        
        self.retries_slider.valueChanged.connect(lambda v: self.retries_label.setText(str(v)))
        
        self.retries_card.hBoxLayout.addWidget(self.retries_label)
        self.retries_card.hBoxLayout.addSpacing(10)
        self.retries_card.hBoxLayout.addWidget(self.retries_slider)
        self.retries_card.hBoxLayout.addSpacing(16)
        
        self.general_group.addSettingCard(self.retries_card)
        self.layout.addWidget(self.general_group)

        # Text Format Settings
        self.format_group = SettingCardGroup("Text Format", self.container)
        
        self.format_switch = SwitchSettingCard(
            FluentIcon.EDIT,
            "Enable Text Format",
            "Format prompt text automatically",
            parent=self.format_group
        )
        self.format_switch.setChecked(cfg.get("text_format_enabled", False))
        self.format_group.addSettingCard(self.format_switch)
        
        self.font_size_card = SettingCard(
            FluentIcon.FONT,
            "Font Size",
            "Size of formatted text (8-72)",
            self.format_group
        )
        self.font_size_slider = Slider(Qt.Horizontal, self.font_size_card)
        self.font_size_slider.setRange(8, 72)
        self.font_size_slider.setValue(cfg.get("text_font_size", 12))
        self.font_size_slider.setFixedWidth(150)
        
        self.font_size_label = QLabel(str(cfg.get("text_font_size", 12)), self.font_size_card)
        self.font_size_label.setFixedWidth(30)
        
        self.font_size_slider.valueChanged.connect(lambda v: self.font_size_label.setText(str(v)))
        
        self.font_size_card.hBoxLayout.addWidget(self.font_size_label)
        self.font_size_card.hBoxLayout.addSpacing(10)
        self.font_size_card.hBoxLayout.addWidget(self.font_size_slider)
        self.font_size_card.hBoxLayout.addSpacing(16)
        self.format_group.addSettingCard(self.font_size_card)
        
        self.wrap_switch = SwitchSettingCard(
            FluentIcon.ALIGNMENT,
            "Auto Text Wrap",
            "Automatically wrap text after formatting",
            parent=self.format_group
        )
        self.wrap_switch.setChecked(cfg.get("text_auto_wrap", True))
        self.format_group.addSettingCard(self.wrap_switch)
        self.layout.addWidget(self.format_group)

        # API Settings
        self.api_group = SettingCardGroup("API Configuration", self.container)
        
        # Base URL
        self.url_card = PushSettingCard(
            "Edit",
            FluentIcon.GLOBE,
            "API Base URL",
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
            "Edit",
            FluentIcon.VPN,
            "API Key",
            "Enter your API Key here",
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
        self.output_group = SettingCardGroup("Output Configuration", self.container)
        
        self.path_card = PushSettingCard(
            "Choose Folder",
            FluentIcon.FOLDER,
            "Output Folder",
            cfg.get("output_folder"),
            self.output_group
        )
        self.path_card.clicked.connect(self.choose_folder)
        
        self.output_group.addSettingCard(self.path_card)
        self.layout.addWidget(self.output_group)

        # Save Button
        self.save_btn = PrimaryPushButton("Save Settings")
        self.save_btn.clicked.connect(self.save_settings)
        self.save_btn.setFixedWidth(200)
        self.layout.addWidget(self.save_btn, 0, Qt.AlignRight)
        
        self.layout.addStretch()

    def choose_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Output Folder", cfg.get("output_folder"))
        if folder:
            self.path_card.setContent(folder)
            cfg.set("output_folder", folder)

    def save_settings(self):
        url = self.url_edit.text().strip()
        key = self.key_edit.text().strip()
        
        cfg.set("api_base_url", url)
        cfg.set("api_key", key)
        cfg.set("max_retries", self.retries_slider.value())
        cfg.set("text_format_enabled", self.format_switch.isChecked())
        cfg.set("text_font_size", self.font_size_slider.value())
        cfg.set("text_auto_wrap", self.wrap_switch.isChecked())
        
        InfoBar.success(
            title='Settings Saved',
            content="Configuration has been updated successfully.",
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP_RIGHT,
            duration=2000,
            parent=self
        )
        cfg.set("api_key", key)
        
        InfoBar.success(
            title="Saved",
            content="Settings have been saved successfully.",
            parent=self,
            position=InfoBarPosition.TOP_RIGHT
        )
