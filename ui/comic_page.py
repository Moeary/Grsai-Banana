import os

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import (
    BodyLabel,
    CaptionLabel,
    CardWidget,
    CheckBox,
    ComboBox,
    FluentIcon,
    InfoBar,
    InfoBarPosition,
    PrimaryPushButton,
    SegmentedWidget,
    StrongBodyLabel,
    TextEdit,
    TransparentToolButton,
    isDarkTheme,
    qconfig,
)

from core.comic_planner import ComicPlanWorker
from core.comic_project_manager import project_manager
from core.config import cfg
from core.i18n import tr
from core.model_catalog import (
    CHAT_MODELS,
    COMIC_IMAGE_MODELS,
    COMPLETION_MODELS,
    LEGACY_IMAGE_MODEL_ALIASES,
    NANO_IMAGE_SIZE_OPTIONS,
)
from core.task_manager import task_manager
from ui.components.image_drop_area import ImageDropArea
from ui.components.task_widget import TaskListWidget, TaskWidget


GPT_IMAGE_SIZE_OPTIONS = ["auto", "1:1", "3:2", "2:3"]


def _parse_reference_targets(text):
    values = []
    for raw in (text or "").replace("，", ",").split(","):
        cleaned = raw.strip()
        if not cleaned:
            continue
        try:
            value = int(cleaned)
        except ValueError:
            continue
        if value > 0 and value not in values:
            values.append(value)
    return values


def _format_reference_targets(values):
    return ",".join(str(value) for value in values or [])


def _reference_label(value):
    labels = {
        1: "一",
        2: "二",
        3: "三",
        4: "四",
        5: "五",
        6: "六",
        7: "七",
        8: "八",
        9: "九",
        10: "十",
        11: "十一",
        12: "十二",
        13: "十三",
        14: "十四",
    }
    return labels.get(value, str(value))


class ComicPageListWidget(QListWidget):
    orderChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragDropMode(QAbstractItemView.InternalMove)
        self.setDefaultDropAction(Qt.MoveAction)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.setSpacing(10)
        self.setStyleSheet(
            """
            QListWidget {
                border: none;
                background: transparent;
                outline: none;
            }
            QListWidget::item {
                background: transparent;
                border: none;
            }
            """
        )

    def dropEvent(self, event):
        super().dropEvent(event)
        self.orderChanged.emit()


class ComicPageCard(CardWidget):
    generateRequested = Signal(dict)

    def __init__(self, page_data, parent=None):
        super().__init__(parent)
        self.page_data = dict(page_data)
        self.page_number = int(page_data.get("page_number", 1))
        self._init_ui(page_data)

    def _init_ui(self, page_data):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        header = QHBoxLayout()
        self.page_label = StrongBodyLabel(tr("comic.page_label", page=self.page_number))
        header.addWidget(self.page_label)
        header.addStretch()
        generate_btn = PrimaryPushButton(tr("comic.generate_page"))
        generate_btn.clicked.connect(self._emit_generate)
        header.addWidget(generate_btn)
        layout.addLayout(header)

        self.title_edit = QLineEdit(page_data.get("title", ""))
        self.title_edit.setPlaceholderText(tr("comic.page_title_placeholder"))
        layout.addWidget(self._field_block(tr("comic.page_title"), self.title_edit))

        self.story_edit = self._make_text_edit(page_data.get("story_beat", ""), 92)
        layout.addWidget(self._field_block(tr("comic.page_story"), self.story_edit))

        self.dialogue_edit = self._make_text_edit("\n".join(page_data.get("dialogue", [])), 96)
        layout.addWidget(self._field_block(tr("comic.page_dialogue"), self.dialogue_edit))

        self.refs_edit = QLineEdit(_format_reference_targets(page_data.get("reference_targets", [])))
        self.refs_edit.setPlaceholderText(tr("comic.page_refs_placeholder"))
        layout.addWidget(self._field_block(tr("comic.page_refs"), self.refs_edit))

        self.prompt_edit = self._make_text_edit(page_data.get("image_prompt", ""), 150)
        layout.addWidget(self._field_block(tr("comic.page_prompt"), self.prompt_edit))

    def _make_text_edit(self, text, height):
        editor = TextEdit()
        editor.setPlainText(text)
        editor.setFixedHeight(height)
        return editor

    def _field_block(self, label_text, widget):
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        layout.addWidget(CaptionLabel(label_text))
        layout.addWidget(widget)
        return container

    def _emit_generate(self):
        self.generateRequested.emit(self.get_page_data())

    def set_page_number(self, page_number):
        self.page_number = int(page_number)
        self.page_label.setText(tr("comic.page_label", page=self.page_number))

    def get_page_data(self):
        dialogue_lines = []
        for line in self.dialogue_edit.toPlainText().splitlines():
            cleaned = line.strip().lstrip("-").lstrip("•").strip()
            if cleaned:
                dialogue_lines.append(cleaned)
        page_data = dict(self.page_data)
        page_data.update({
            "page_number": self.page_number,
            "title": self.title_edit.text().strip(),
            "story_beat": self.story_edit.toPlainText().strip(),
            "dialogue": dialogue_lines,
            "reference_targets": _parse_reference_targets(self.refs_edit.text()),
            "image_prompt": self.prompt_edit.toPlainText().strip(),
        })
        return page_data


class ComicPage(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("ComicPage")
        self.task_counter = 0
        self.plan_worker = None
        self.page_cards = []
        self.running_generation_tasks = set()
        self.current_plan_title = ""
        self.current_plan_style_notes = ""
        self.generated_outputs = {}
        self.current_project_root = ""
        self.current_project_pages_dir = ""
        self.init_ui()
        self.refresh_project_list()

    def init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)

        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(15)

        self.project_card = CardWidget()
        self.update_card_style(self.project_card)
        qconfig.themeChanged.connect(lambda: self.update_card_style(self.project_card))
        project_layout = QVBoxLayout(self.project_card)
        project_layout.setSpacing(8)
        project_layout.addWidget(StrongBodyLabel(tr("comic.project_title")))

        project_name_row = QHBoxLayout()
        self.project_name_edit = QLineEdit()
        self.project_name_edit.setPlaceholderText(tr("comic.project_name_placeholder"))
        self.project_name_edit.setText(cfg.get("comic_last_project", ""))
        project_name_row.addWidget(self.project_name_edit, 1)
        self.save_project_btn = PrimaryPushButton(tr("comic.save_project"))
        self.save_project_btn.clicked.connect(lambda: self.save_project_state(show_feedback=True))
        project_name_row.addWidget(self.save_project_btn)
        project_layout.addLayout(project_name_row)

        project_load_row = QHBoxLayout()
        self.project_combo = ComboBox()
        project_load_row.addWidget(self.project_combo, 1)
        self.load_project_btn = PrimaryPushButton(tr("comic.load_project"))
        self.load_project_btn.clicked.connect(self.load_selected_project)
        project_load_row.addWidget(self.load_project_btn)
        self.refresh_project_btn = TransparentToolButton(FluentIcon.SYNC)
        self.refresh_project_btn.clicked.connect(self.refresh_project_list)
        project_load_row.addWidget(self.refresh_project_btn)
        project_layout.addLayout(project_load_row)

        self.settings_card = CardWidget()
        self.update_card_style(self.settings_card)
        qconfig.themeChanged.connect(lambda: self.update_card_style(self.settings_card))
        settings_layout = QVBoxLayout(self.settings_card)
        settings_layout.setSpacing(8)

        row_1 = QHBoxLayout()
        story_model_box = QVBoxLayout()
        story_model_box.addWidget(CaptionLabel(tr("comic.story_model")))
        self.story_model_combo = ComboBox()
        self.story_model_combo.addItems(CHAT_MODELS)
        self.story_model_combo.setCurrentText(cfg.get("comic_story_model", CHAT_MODELS[0]))
        story_model_box.addWidget(self.story_model_combo)
        row_1.addLayout(story_model_box)

        image_model_box = QVBoxLayout()
        image_model_box.addWidget(CaptionLabel(tr("comic.image_model")))
        self.image_model_combo = ComboBox()
        self.image_model_combo.addItems(COMIC_IMAGE_MODELS)
        raw_preferred_image_model = cfg.get("comic_image_model", COMIC_IMAGE_MODELS[0])
        preferred_image_model = LEGACY_IMAGE_MODEL_ALIASES.get(raw_preferred_image_model, raw_preferred_image_model)
        if preferred_image_model in COMIC_IMAGE_MODELS:
            self.image_model_combo.setCurrentText(preferred_image_model)
        self.image_model_combo.currentTextChanged.connect(self.on_image_model_changed)
        image_model_box.addWidget(self.image_model_combo)
        row_1.addLayout(image_model_box)
        settings_layout.addLayout(row_1)

        row_2 = QHBoxLayout()
        pages_box = QVBoxLayout()
        pages_box.addWidget(CaptionLabel(tr("comic.page_count")))
        self.page_count_combo = ComboBox()
        self.page_count_combo.addItems([str(i) for i in range(2, 13)])
        self.page_count_combo.setCurrentText(str(cfg.get("comic_page_count", 6)))
        pages_box.addWidget(self.page_count_combo)
        row_2.addLayout(pages_box)

        ratio_box = QVBoxLayout()
        self.ratio_label = CaptionLabel(tr("comic.aspect_ratio"))
        ratio_box.addWidget(self.ratio_label)
        self.ratio_combo = ComboBox()
        self.ratio_combo.addItems(["auto", "1:1", "16:9", "9:16", "4:3", "3:4", "3:2", "2:3", "5:4", "4:5", "21:9"])
        self.ratio_combo.setCurrentText(cfg.get("comic_aspect_ratio", "3:4"))
        ratio_box.addWidget(self.ratio_combo)
        row_2.addLayout(ratio_box)

        size_box = QVBoxLayout()
        self.size_label = CaptionLabel(tr("comic.image_size"))
        size_box.addWidget(self.size_label)
        self.size_combo = ComboBox()
        self.size_combo.addItems(["1K", "2K", "4K"])
        self.size_combo.setCurrentText(cfg.get("comic_image_size", "1K"))
        size_box.addWidget(self.size_combo)
        row_2.addLayout(size_box)
        settings_layout.addLayout(row_2)

        self.auto_retry_cb = CheckBox(tr("comic.auto_retry"))
        self.auto_retry_cb.setChecked(cfg.get("auto_retry_on_failure", False))
        settings_layout.addWidget(self.auto_retry_cb)

        left_layout.addWidget(self.project_card)
        left_layout.addWidget(self.settings_card)

        self.story_editor = self._build_editor_card(
            tr("comic.story_requirement"),
            tr("comic.story_requirement_placeholder"),
            160,
        )
        left_layout.addWidget(self.story_editor["card"])

        self.style_editor = self._build_editor_card(
            tr("comic.style_notes"),
            tr("comic.style_notes_placeholder"),
            120,
        )
        left_layout.addWidget(self.style_editor["card"])

        refs_card = CardWidget()
        self.update_card_style(refs_card)
        qconfig.themeChanged.connect(lambda: self.update_card_style(refs_card))
        refs_layout = QVBoxLayout(refs_card)
        refs_header = QHBoxLayout()
        refs_header.addWidget(StrongBodyLabel(tr("comic.reference_images")))
        refs_header.addStretch()
        paste_btn = TransparentToolButton(FluentIcon.PASTE)
        paste_btn.setToolTip(tr("drop.tooltip.paste"))
        paste_btn.clicked.connect(self.on_image_paste)
        refs_header.addWidget(paste_btn)
        clear_btn = TransparentToolButton(FluentIcon.DELETE)
        clear_btn.setToolTip(tr("drop.tooltip.clear"))
        clear_btn.clicked.connect(self.on_image_clear)
        refs_header.addWidget(clear_btn)
        refs_layout.addLayout(refs_header)
        self.drop_area = ImageDropArea()
        self.drop_area.setMinimumHeight(420)
        self.drop_area.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        refs_layout.addWidget(self.drop_area, 1)
        left_layout.addWidget(refs_card, 1)

        buttons_row = QHBoxLayout()
        self.plan_btn = PrimaryPushButton(tr("comic.plan_story"))
        self.plan_btn.clicked.connect(self.on_plan_story)
        buttons_row.addWidget(self.plan_btn)
        self.generate_all_btn = PrimaryPushButton(tr("comic.generate_all"))
        self.generate_all_btn.clicked.connect(self.on_generate_all)
        buttons_row.addWidget(self.generate_all_btn)
        left_layout.addLayout(buttons_row)

        center_panel = QWidget()
        center_layout = QVBoxLayout(center_panel)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(10)

        pages_header = QHBoxLayout()
        pages_header.addWidget(StrongBodyLabel(tr("comic.pages_title")))
        pages_header.addStretch()
        self.plan_status_label = CaptionLabel(tr("comic.no_pages"))
        pages_header.addWidget(self.plan_status_label)
        center_layout.addLayout(pages_header)

        self.pages_empty_label = BodyLabel(tr("comic.no_pages"))
        self.pages_empty_label.setAlignment(Qt.AlignCenter)
        center_layout.addWidget(self.pages_empty_label, 1)

        self.pages_list = ComicPageListWidget()
        self.pages_list.orderChanged.connect(self.on_pages_reordered)
        center_layout.addWidget(self.pages_list, 1)

        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(10)
        task_tabs = SegmentedWidget()
        task_tabs.addItem("comic_task_list", tr("comic.task_list"))
        task_tabs.setCurrentItem("comic_task_list")
        task_tabs.setEnabled(False)
        right_layout.addWidget(task_tabs)
        self.task_list_widget = TaskListWidget()
        right_layout.addWidget(self.task_list_widget, 1)

        main_layout.addWidget(left_panel, 3)
        main_layout.addWidget(center_panel, 4)
        main_layout.addWidget(right_panel, 2)

        self.on_image_model_changed(self.image_model_combo.currentText())
        self._show_empty_pages_message()

    def _build_editor_card(self, title, placeholder, min_height):
        card = CardWidget()
        self.update_card_style(card)
        qconfig.themeChanged.connect(lambda: self.update_card_style(card))
        layout = QVBoxLayout(card)
        layout.addWidget(StrongBodyLabel(title))
        editor = TextEdit()
        editor.setPlaceholderText(placeholder)
        editor.setMinimumHeight(min_height)
        layout.addWidget(editor)
        return {"card": card, "editor": editor}

    def update_card_style(self, card_widget):
        if isDarkTheme():
            bg_color = "rgba(255, 255, 255, 0.06)"
        else:
            bg_color = "rgb(255, 255, 255)"
        card_widget.setStyleSheet(f"CardWidget {{ background-color: {bg_color}; }}")

    def refresh_project_list(self):
        projects = project_manager.list_projects()
        self.project_combo.blockSignals(True)
        self.project_combo.clear()
        if projects:
            self.project_combo.addItems(projects)
            last_project = cfg.get("comic_last_project", "")
            if last_project in projects:
                self.project_combo.setCurrentText(last_project)
        self.project_combo.blockSignals(False)

    def _current_project_name(self):
        return self.project_name_edit.text().strip()

    def _collect_pages_data(self):
        self._sync_page_cards_from_list()
        return [card.get_page_data() for card in self.page_cards]

    def _is_completion_model(self, model_name):
        normalized_model = LEGACY_IMAGE_MODEL_ALIASES.get(model_name, model_name)
        return normalized_model in COMPLETION_MODELS or normalized_model.startswith("gpt-image")

    def _set_combo_items(self, combo, items, preferred=None):
        combo.blockSignals(True)
        combo.clear()
        combo.addItems(items)
        if preferred in items:
            combo.setCurrentText(preferred)
        elif items:
            combo.setCurrentText(items[0])
        combo.blockSignals(False)

    def _sync_page_cards_from_list(self):
        cards = []
        for row in range(self.pages_list.count()):
            item = self.pages_list.item(row)
            card = self.pages_list.itemWidget(item)
            if isinstance(card, ComicPageCard):
                cards.append(card)
        if cards:
            self.page_cards = cards
        return self.page_cards

    def _refresh_page_numbers(self):
        self._sync_page_cards_from_list()
        for index, card in enumerate(self.page_cards, start=1):
            card.set_page_number(index)
            item = self.pages_list.item(index - 1)
            if item is not None:
                item.setSizeHint(card.sizeHint())

    def _ensure_project_name(self):
        if self._current_project_name():
            return True
        InfoBar.warning(
            title=tr("common.warning"),
            content=tr("comic.project_name_required"),
            parent=self,
            position=InfoBarPosition.TOP_RIGHT,
        )
        return False

    def _project_settings_payload(self):
        return {
            "story_model": self.story_model_combo.currentText(),
            "image_model": self.image_model_combo.currentText(),
            "page_count": int(self.page_count_combo.currentText()),
            "aspect_ratio": self.ratio_combo.currentText(),
            "image_size": self.size_combo.currentText() if self.size_combo.isVisible() else "1K",
            "auto_retry": self.auto_retry_cb.isChecked(),
        }

    def on_image_model_changed(self, model_name):
        if not model_name:
            return
        model_name = LEGACY_IMAGE_MODEL_ALIASES.get(model_name, model_name)
        cfg.set("comic_image_model", model_name)
        is_completion = self._is_completion_model(model_name)

        self.ratio_label.setVisible(not is_completion)
        self.ratio_combo.setVisible(not is_completion)

        size_options = GPT_IMAGE_SIZE_OPTIONS if is_completion else NANO_IMAGE_SIZE_OPTIONS.get(model_name)
        has_size_options = bool(size_options)
        self.size_label.setVisible(has_size_options)
        self.size_combo.setVisible(has_size_options)
        if has_size_options:
            selected_size = cfg.get("gpt_image_size", "auto") if is_completion else cfg.get("comic_image_size", "1K")
            if selected_size not in size_options:
                selected_size = size_options[0]
            self._set_combo_items(self.size_combo, size_options, selected_size)

    def _story_requirement(self):
        return self.story_editor["editor"].toPlainText().strip()

    def _style_notes(self):
        return self.style_editor["editor"].toPlainText().strip()

    def _save_current_settings(self):
        image_model = LEGACY_IMAGE_MODEL_ALIASES.get(self.image_model_combo.currentText(), self.image_model_combo.currentText())
        cfg.set("comic_story_model", self.story_model_combo.currentText())
        cfg.set("comic_image_model", image_model)
        cfg.set("comic_page_count", int(self.page_count_combo.currentText()))
        cfg.set("comic_aspect_ratio", self.ratio_combo.currentText())
        cfg.set("comic_last_project", self._current_project_name())
        if self.size_combo.isVisible():
            if self._is_completion_model(image_model):
                cfg.set("gpt_image_size", self.size_combo.currentText())
            else:
                cfg.set("comic_image_size", self.size_combo.currentText())

    def save_project_state(self, show_feedback=False):
        project_name = self._current_project_name()
        if not project_name:
            if show_feedback:
                InfoBar.warning(
                    title=tr("common.warning"),
                    content=tr("comic.project_name_required"),
                    parent=self,
                    position=InfoBarPosition.TOP_RIGHT,
                )
            return None

        self._save_current_settings()
        saved = project_manager.save_project(
            project_name,
            {
                "story_requirement": self._story_requirement(),
                "style_notes": self._style_notes(),
                "plan_title": self.current_plan_title,
                "plan_style_notes": self.current_plan_style_notes,
                "settings": self._project_settings_payload(),
                "pages": self._collect_pages_data(),
                "reference_images": list(self.drop_area.image_paths),
                "generated_outputs": self.generated_outputs,
            },
        )
        self.current_project_root = saved["project_root"]
        self.current_project_pages_dir = saved["pages_dir"]
        self.project_name_edit.setText(saved["project_name"])
        cfg.set("comic_last_project", saved["project_name"])
        self.refresh_project_list()
        self.project_combo.setCurrentText(saved["project_name"])

        if show_feedback:
            InfoBar.success(
                title=tr("common.success"),
                content=tr("comic.project_saved", name=saved["project_name"]),
                parent=self,
                position=InfoBarPosition.TOP_RIGHT,
            )
        return saved

    def load_selected_project(self):
        project_name = self.project_combo.currentText().strip()
        if not project_name:
            InfoBar.warning(
                title=tr("common.warning"),
                content=tr("comic.project_select_required"),
                parent=self,
                position=InfoBarPosition.TOP_RIGHT,
            )
            return

        payload = project_manager.load_project(project_name)
        settings = payload.get("settings", {})

        self.project_name_edit.setText(payload.get("project_name", project_name))
        self.story_editor["editor"].setPlainText(payload.get("story_requirement", ""))
        self.style_editor["editor"].setPlainText(payload.get("style_notes", ""))
        self.story_model_combo.setCurrentText(settings.get("story_model", cfg.get("comic_story_model", CHAT_MODELS[0])))
        raw_image_model = settings.get("image_model", cfg.get("comic_image_model", COMIC_IMAGE_MODELS[0]))
        image_model = LEGACY_IMAGE_MODEL_ALIASES.get(raw_image_model, raw_image_model)
        if image_model in COMIC_IMAGE_MODELS:
            self.image_model_combo.setCurrentText(image_model)
        self.page_count_combo.setCurrentText(str(settings.get("page_count", cfg.get("comic_page_count", 6))))
        self.ratio_combo.setCurrentText(settings.get("aspect_ratio", cfg.get("comic_aspect_ratio", "3:4")))
        self.auto_retry_cb.setChecked(bool(settings.get("auto_retry", cfg.get("auto_retry_on_failure", False))))
        self.on_image_model_changed(self.image_model_combo.currentText())
        if self.size_combo.isVisible():
            saved_size = settings.get("image_size")
            if saved_size and self.size_combo.findText(saved_size) >= 0:
                self.size_combo.setCurrentText(saved_size)

        self.drop_area.clear_images()
        for ref_path in payload.get("resolved_reference_images", []):
            self.drop_area.add_image(ref_path)

        self.current_plan_title = payload.get("plan_title", "")
        self.current_plan_style_notes = payload.get("plan_style_notes", "")
        self.generated_outputs = payload.get("generated_outputs", {})
        self.current_project_root = payload.get("project_root", "")
        self.current_project_pages_dir = payload.get("pages_dir", "")
        self._populate_pages(payload.get("pages", []))
        self.plan_status_label.setText(tr("comic.project_loaded", name=project_name))
        cfg.set("comic_last_project", project_name)

        InfoBar.success(
            title=tr("common.success"),
            content=tr("comic.project_loaded", name=project_name),
            parent=self,
            position=InfoBarPosition.TOP_RIGHT,
        )

    def on_plan_story(self):
        if not self._ensure_project_name():
            return
        story_requirement = self._story_requirement()
        if not story_requirement:
            InfoBar.warning(
                title=tr("common.warning"),
                content=tr("comic.enter_story_warning"),
                parent=self,
                position=InfoBarPosition.TOP_RIGHT,
            )
            return

        self.generated_outputs = {}
        self.save_project_state(show_feedback=False)
        self.plan_btn.setEnabled(False)
        self.plan_status_label.setText(tr("comic.planning"))

        self.plan_worker = ComicPlanWorker(
            self.story_model_combo.currentText(),
            story_requirement,
            self._style_notes(),
            int(self.page_count_combo.currentText()),
            list(self.drop_area.image_paths),
        )
        self.plan_worker.finished_signal.connect(self.on_plan_finished)
        self.plan_worker.finished.connect(self.on_plan_worker_finished)
        self.plan_worker.start()

    def on_plan_finished(self, success, plan, message):
        if not success:
            self.plan_status_label.setText(tr("comic.plan_failed"))
            InfoBar.warning(
                title=tr("common.warning"),
                content=message or tr("comic.plan_failed"),
                parent=self,
                position=InfoBarPosition.TOP_RIGHT,
            )
            return

        self.current_plan_title = plan.get("title", "").strip()
        self.current_plan_style_notes = plan.get("style_notes", "").strip()
        self._populate_pages(plan.get("pages", []))
        self.save_project_state(show_feedback=False)
        self.plan_status_label.setText(tr("comic.plan_ready", count=len(self.page_cards)))
        InfoBar.success(
            title=tr("common.success"),
            content=tr("comic.plan_success", count=len(self.page_cards)),
            parent=self,
            position=InfoBarPosition.TOP_RIGHT,
        )

    def on_plan_worker_finished(self):
        self.plan_btn.setEnabled(True)
        self.plan_worker = None

    def _clear_page_cards(self):
        self.page_cards = []
        self.pages_list.clear()

    def _show_empty_pages_message(self):
        self._clear_page_cards()
        self.pages_empty_label.setText(tr("comic.no_pages"))
        self.pages_empty_label.show()
        self.pages_list.hide()

    def _populate_pages(self, pages):
        self._clear_page_cards()
        if not pages:
            self._show_empty_pages_message()
            return

        for page in pages:
            card = ComicPageCard(page)
            card.generateRequested.connect(self.generate_single_page)
            item = QListWidgetItem()
            item.setSizeHint(card.sizeHint())
            self.pages_list.addItem(item)
            self.pages_list.setItemWidget(item, card)
            self.page_cards.append(card)

        self._refresh_page_numbers()
        self.pages_empty_label.hide()
        self.pages_list.show()

    def on_pages_reordered(self):
        self._refresh_page_numbers()
        if self.page_cards:
            self.save_project_state(show_feedback=False)

    def on_generate_all(self):
        if not self._ensure_project_name():
            return
        if not self.page_cards:
            InfoBar.warning(
                title=tr("common.warning"),
                content=tr("comic.no_pages_to_generate"),
                parent=self,
                position=InfoBarPosition.TOP_RIGHT,
            )
            return

        self.save_project_state(show_feedback=False)
        for card in self.page_cards:
            self._launch_task_for_page(card.get_page_data())

    def generate_single_page(self, page_data):
        if not self._ensure_project_name():
            return
        self.save_project_state(show_feedback=False)
        self._launch_task_for_page(page_data)

    def _project_pages_dir(self):
        saved = self.save_project_state(show_feedback=False)
        if saved:
            return saved["pages_dir"]
        return ""

    def _build_image_params(self, page_data):
        model = LEGACY_IMAGE_MODEL_ALIASES.get(self.image_model_combo.currentText(), self.image_model_combo.currentText())
        size = self.size_combo.currentText() if self.size_combo.isVisible() else "1K"
        ratio = "auto" if self._is_completion_model(model) else self.ratio_combo.currentText()
        page_number = int(page_data.get("page_number", 1))
        return {
            "model": model,
            "ratio": ratio,
            "size": size,
            "ref_urls": [path for path in self.drop_area.image_paths if os.path.isfile(path)],
            "variants": 1,
            "page_number": page_number,
            "output_dir": self._project_pages_dir(),
            "filename_prefix": f"page_{page_number:02d}",
        }

    def _build_final_prompt(self, page_data):
        parts = []
        if self.current_plan_title:
            parts.append(f"项目名：{self.current_plan_title}。")
        parts.append(f"这是漫画的第 {page_data.get('page_number', 1)} 页。")
        reference_targets = page_data.get("reference_targets") or []
        if self.drop_area.image_paths:
            parts.append("你会同时收到多张按上传顺序排列的人物参考图：第 1 张就是参考图一，第 2 张就是参考图二，后续依次类推。")
            if reference_targets:
                refs_text = "、".join(f"参考图{_reference_label(index)}" for index in reference_targets)
                parts.append(f"本页主要角色请优先严格参考：{refs_text}。未列出的参考图不要误用到当前主角身上。")
            parts.append("请先逐张识别参考图，再决定当前页面该使用哪位角色的外观，不要混淆不同参考图中的发色、眼镜、服装和配饰。")
        if page_data.get("story_beat"):
            parts.append(f"本页剧情：{page_data['story_beat']}。")
        if page_data.get("dialogue"):
            parts.append("本页对白要点：" + " ".join(page_data["dialogue"]))
        if self.current_plan_style_notes:
            parts.append(f"全局画风与氛围：{self.current_plan_style_notes}。")
        parts.append(page_data.get("image_prompt", ""))
        parts.append("请输出完整漫画页画面，保证阅读顺序清楚、叙事明确、人物表演到位、画面张力强。")
        return " ".join(part for part in parts if part and str(part).strip())

    def _launch_task_for_page(self, page_data):
        params = self._build_image_params(page_data)
        prompt = self._build_final_prompt(page_data)

        self.task_counter += 1
        task_widget = TaskWidget(self.task_counter, prompt, params)
        task_widget.auto_retry = self.auto_retry_cb.isChecked()
        task_widget.index_label.setText(f"P{page_data.get('page_number', 1)}")
        task_widget.retry_requested.connect(self.retry_task)
        task_widget.regenerate_requested.connect(self.regenerate_task)
        self.task_list_widget.add_task(task_widget)
        self.running_generation_tasks.add(task_widget)
        self.start_worker(task_widget)

    def start_worker(self, task_widget):
        try:
            worker = task_manager.create_worker(
                task_widget.prompt,
                task_widget.params["model"],
                task_widget.params["ratio"],
                task_widget.params["size"],
                task_widget.params["ref_urls"],
                variants=task_widget.params.get("variants", 1),
                output_dir=task_widget.params.get("output_dir"),
                filename_prefix=task_widget.params.get("filename_prefix"),
            )
            task_widget.progress_ring.show()
            task_widget.progress_ring.setValue(0)
            task_widget.status_label.setText(tr("comic.task_starting"))
            worker.progress_signal.connect(task_widget.update_progress)
            worker.finished_signal.connect(lambda s, r, m: self.on_worker_finished(task_widget, s, r, m))
            worker.finished.connect(lambda: self.cleanup_worker(task_widget))
            task_manager.register_worker(task_widget, worker)
            worker.start()
        except Exception as e:
            self.running_generation_tasks.discard(task_widget)
            print(f"[ComicPage] Error in start_worker: {e}")

    def on_worker_finished(self, task_widget, success, result, message):
        if success:
            task_widget.set_success(result)
            page_number = str(task_widget.params.get("page_number", ""))
            if page_number:
                self.generated_outputs.setdefault(page_number, []).append(result)
                self.save_project_state(show_feedback=False)
        else:
            task_widget.set_failed(result, message)

    def cleanup_worker(self, task_widget):
        task_manager.unregister_worker(task_widget)
        self.running_generation_tasks.discard(task_widget)

    def retry_task(self, task_widget):
        self.running_generation_tasks.add(task_widget)
        self.start_worker(task_widget)

    def regenerate_task(self, task_widget):
        self.task_counter += 1
        new_widget = TaskWidget(self.task_counter, task_widget.prompt, task_widget.params.copy())
        new_widget.auto_retry = self.auto_retry_cb.isChecked()
        new_widget.index_label.setText(task_widget.index_label.text())
        new_widget.retry_requested.connect(self.retry_task)
        new_widget.regenerate_requested.connect(self.regenerate_task)
        self.task_list_widget.add_task(new_widget)
        self.running_generation_tasks.add(new_widget)
        self.start_worker(new_widget)

    def on_image_paste(self):
        self.drop_area.paste_from_clipboard()
        self.save_project_state(show_feedback=False)

    def on_image_clear(self):
        self.drop_area.clear_images()
        self.save_project_state(show_feedback=False)

    def stop_all_workers(self):
        if self.plan_worker and self.plan_worker.isRunning():
            self.plan_worker.quit()
            self.plan_worker.wait(1000)
