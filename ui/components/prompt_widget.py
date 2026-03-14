from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QSizePolicy, QApplication
from PySide6.QtGui import QFont, QTextOption
from qfluentwidgets import TextEdit, StrongBodyLabel, TransparentToolButton, FluentIcon, InfoBar, InfoBarPosition, isDarkTheme, qconfig
from core.config import cfg
from core.i18n import tr

class PromptWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        
        # Header
        header_layout = QHBoxLayout()
        self.title_label = StrongBodyLabel(tr("prompt.title"))
        header_layout.addWidget(self.title_label)
        header_layout.addStretch()
        
        self.paste_btn = TransparentToolButton(FluentIcon.PASTE)
        self.paste_btn.setToolTip(tr("prompt.tooltip.paste"))
        self.paste_btn.clicked.connect(self.paste_from_clipboard)
        header_layout.addWidget(self.paste_btn)

        self.format_btn = TransparentToolButton(FluentIcon.EDIT)
        self.format_btn.setToolTip(tr("prompt.tooltip.format"))
        self.format_btn.clicked.connect(self.normalize_prompt_format)
        header_layout.addWidget(self.format_btn)
        
        self.clear_btn = TransparentToolButton(FluentIcon.DELETE)
        self.clear_btn.setToolTip(tr("prompt.tooltip.clear"))
        self.clear_btn.clicked.connect(self.clear_prompt)
        header_layout.addWidget(self.clear_btn)
        
        layout.addLayout(header_layout)
        
        # Text Edit
        self.prompt_edit = TextEdit()
        self.prompt_edit.setPlaceholderText(tr("prompt.placeholder"))
        self.prompt_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.update_prompt_edit_style()
        qconfig.themeChanged.connect(self.update_prompt_edit_style)
        
        self._apply_text_formatting()
        
        layout.addWidget(self.prompt_edit)

    def get_prompt(self):
        return self.prompt_edit.toPlainText().strip()

    def set_prompt(self, text):
        self.prompt_edit.setPlainText(text)

    def paste_from_clipboard(self):
        clipboard = QApplication.clipboard()
        text = clipboard.text()
        if text:
            self.prompt_edit.insertPlainText(text)
            self._apply_text_formatting()
            InfoBar.success(title=tr("common.pasted"), content=tr("prompt.msg.pasted"), parent=self, position=InfoBarPosition.TOP_RIGHT)

    def clear_prompt(self):
        self.prompt_edit.clear()
        font = QFont()
        self.prompt_edit.setFont(font)
        self.prompt_edit.setWordWrapMode(QTextOption.WordWrap)
        InfoBar.success(title=tr("common.cleared"), content=tr("prompt.msg.cleared"), parent=self, position=InfoBarPosition.TOP_RIGHT)

    def normalize_prompt_format(self):
        """Strip rich text formatting and re-apply configured plain-text style."""
        plain_text = self.prompt_edit.toPlainText()
        cursor = self.prompt_edit.textCursor()
        cursor_pos = cursor.position()

        self.prompt_edit.setPlainText(plain_text)
        self._apply_text_formatting()

        cursor = self.prompt_edit.textCursor()
        cursor.setPosition(min(cursor_pos, len(plain_text)))
        self.prompt_edit.setTextCursor(cursor)

        InfoBar.success(
            title=tr("common.formatted"),
            content=tr("prompt.msg.formatted"),
            parent=self,
            position=InfoBarPosition.TOP_RIGHT
        )

    def _apply_text_formatting(self):
        if cfg.get("text_format_enabled", False):
            font_size = cfg.get("text_font_size", 12)
            font_family = cfg.get("text_font_family", "Arial")
            auto_wrap = cfg.get("text_auto_wrap", True)
            
            font = QFont(font_family)
            font.setPointSize(font_size)
            self.prompt_edit.setFont(font)
            
            if auto_wrap:
                self.prompt_edit.setWordWrapMode(QTextOption.WordWrap)
            else:
                self.prompt_edit.setWordWrapMode(QTextOption.NoWrap)

    def update_text_formatting(self):
        self._apply_text_formatting()

    def update_prompt_edit_style(self):
        """Unify TextEdit background color with other card widgets"""
        if isDarkTheme():
            bg_color = "rgba(255, 255, 255, 0.06)"
            border_color = "rgba(255, 255, 255, 0.1)"
        else:
            bg_color = "rgb(255, 255, 255)"
            border_color = "rgba(0, 0, 0, 0.12)"
        self.prompt_edit.setStyleSheet(f"""
            QTextEdit {{
                background-color: {bg_color};
                border: 1px solid {border_color};
                border-radius: 6px;
            }}
            QTextEdit:focus {{
                background-color: {bg_color};
                border: 1px solid {border_color};
            }}
        """)
