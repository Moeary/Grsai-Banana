from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QFileDialog
from qfluentwidgets import (ScrollArea, SettingCardGroup, LineEdit, PushSettingCard, 
                            FluentIcon, InfoBar, InfoBarPosition, PrimaryPushButton)

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
        
        InfoBar.success(
            title="Saved",
            content="Settings have been saved successfully.",
            parent=self,
            position=InfoBarPosition.TOP_RIGHT
        )
