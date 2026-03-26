import json
import re

from PySide6.QtCore import QThread, Signal

from core.api_client import api
from core.i18n import get_language


def _output_language_name():
    return "简体中文" if get_language() == "zh" else "English"


def _extract_json_payload(content):
    text = (content or "").strip()
    if not text:
        raise ValueError("Empty response from story model.")

    fenced_match = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.DOTALL)
    if fenced_match:
        text = fenced_match.group(1).strip()

    if text.startswith("{") and text.endswith("}"):
        return text

    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        return text[start : end + 1]

    raise ValueError("Story model did not return valid JSON.")


def _normalize_dialogue(dialogue):
    if isinstance(dialogue, list):
        return [str(line).strip() for line in dialogue if str(line).strip()]
    if isinstance(dialogue, str):
        lines = []
        for line in dialogue.splitlines():
            cleaned = line.strip().lstrip("-").lstrip("•").strip()
            if cleaned:
                lines.append(cleaned)
        return lines
    return []


def _fallback_visual_prompt(page, plan_style_notes, total_pages):
    dialogue = page.get("dialogue") or []
    dialogue_text = " ".join(dialogue[:4])
    prompt_parts = [
        "请生成一张完整的漫画页插画。",
        f"这是全篇第 {page.get('page_number', 1)} / {total_pages} 页。",
        "如果提供了人物参考图，请保持人物身份、发型、服装和气质稳定统一。",
        f"本页剧情重点：{page.get('story_beat', '')}",
        f"画面场景：{page.get('scene_description', '')}",
        f"分镜与排版：{page.get('panel_layout', '')}",
        f"镜头与机位：{page.get('camera_direction', '')}",
        f"旁白氛围：{page.get('narration', '')}",
        f"对白要点：{dialogue_text}",
        f"整体画风：{plan_style_notes}",
        "要求叙事清晰、表演生动、画面有戏剧张力、具备漫画页阅读顺序。",
    ]
    return " ".join(part for part in prompt_parts if part and str(part).strip())


def parse_comic_plan(content, page_count):
    payload = json.loads(_extract_json_payload(content))
    pages = payload.get("pages") or []
    if not isinstance(pages, list) or not pages:
        raise ValueError("Story model returned no comic pages.")

    plan_style_notes = str(payload.get("style_notes", "")).strip()
    normalized_pages = []
    for index, page in enumerate(pages, start=1):
        if not isinstance(page, dict):
            continue
        dialogue = _normalize_dialogue(page.get("dialogue"))
        normalized_page = {
            "page_number": int(page.get("page_number") or index),
            "title": str(page.get("title", "")).strip(),
            "story_beat": str(page.get("story_beat", "")).strip(),
            "narration": str(page.get("narration", "")).strip(),
            "dialogue": dialogue,
            "scene_description": str(page.get("scene_description", "")).strip(),
            "camera_direction": str(page.get("camera_direction", "")).strip(),
            "panel_layout": str(page.get("panel_layout", "")).strip(),
            "image_prompt": str(page.get("image_prompt", "")).strip(),
        }
        if not normalized_page["image_prompt"]:
            normalized_page["image_prompt"] = _fallback_visual_prompt(normalized_page, plan_style_notes, max(page_count, len(pages)))
        normalized_pages.append(normalized_page)

    if not normalized_pages:
        raise ValueError("Failed to normalize comic pages from story model output.")

    return {
        "title": str(payload.get("title", "")).strip(),
        "style_notes": plan_style_notes,
        "pages": normalized_pages,
    }


def build_planning_messages(story_requirement, style_notes, page_count, has_reference_images):
    language_name = _output_language_name()
    ref_text = "有" if has_reference_images else "无"
    schema = {
        "title": "短篇标题",
        "style_notes": "全局画风说明",
        "pages": [
            {
                "page_number": 1,
                "title": "可选页面标题，可留空字符串",
                "story_beat": "这一页发生了什么",
                "narration": "旁白，可为空",
                "dialogue": ["角色名：对白"],
                "scene_description": "这一页应该看到什么",
                "camera_direction": "镜头与构图建议",
                "panel_layout": "建议的分镜排版",
                "image_prompt": "可直接用于出图的一整页漫画提示词",
            }
        ],
    }

    system_prompt = (
        "你是一位专业漫画编剧和分镜策划师。"
        "请把用户的故事需求扩写成可直接用于漫画创作的分页脚本。"
        "要求剧情连贯、角色稳定、对白自然、每一页都具备明确的画面目标和可执行的出图提示词。"
        "所有文本字段必须使用简体中文输出，尤其是 title、style_notes、story_beat、narration、dialogue、scene_description、camera_direction、panel_layout、image_prompt。"
        "除用户原文中的专有名词、英文名或必须保留的品牌名外，禁止输出英文句子、英文关键词列表或英文风格描述。"
        "image_prompt 必须是可直接用于出图模型的完整中文提示词，里面要写清人物、场景、动作、情绪、镜头、光影、构图、分镜页感和对白呈现方式。"
        "页面标题不是必需项，如果没有必要可以输出空字符串。"
        "你必须只返回严格 JSON，不要输出 markdown，不要解释，不要多余文本。"
    )
    user_prompt = (
        f"输出语言：{language_name}\n"
        f"目标页数：{page_count}\n"
        f"绘图阶段是否提供人物参考图：{ref_text}\n"
        "请控制主要角色数量，确保角色在全篇视觉上保持一致。\n"
        "每一页都应被设计为完整的漫画页画面，而不是单独角色立绘。\n"
        "请优先把关键信息写进 image_prompt，不要依赖页面标题补充信息。\n"
        "整篇故事必须有起承转合，页与页之间衔接清楚。\n"
        "如果对白里不希望出现角色名字，也请直接在对白文本里避免写名字，不要在 image_prompt 里重复英文台词。\n"
        "再次强调：请不要输出英文提示词，最终 JSON 中每一页的 image_prompt 也必须是自然、完整、可执行的中文描述。\n"
        f"故事需求：\n{story_requirement.strip()}\n\n"
        f"补充风格说明：\n{style_notes.strip() or '无额外要求'}\n\n"
        "请严格按照下面的 JSON 结构返回：\n"
        f"{json.dumps(schema, ensure_ascii=False, indent=2)}"
    )
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]


class ComicPlanWorker(QThread):
    finished_signal = Signal(bool, object, str)

    def __init__(self, story_model, story_requirement, style_notes, page_count, has_reference_images):
        super().__init__()
        self.story_model = story_model
        self.story_requirement = story_requirement
        self.style_notes = style_notes
        self.page_count = page_count
        self.has_reference_images = has_reference_images

    def run(self):
        try:
            messages = build_planning_messages(
                self.story_requirement,
                self.style_notes,
                self.page_count,
                self.has_reference_images,
            )
            response = api.chat_completion(
                self.story_model,
                messages,
                stream=False,
                temperature=0.8,
            )
            if response.get("error"):
                message = response["error"].get("message", "Story planning failed.")
                self.finished_signal.emit(False, None, message)
                return

            choices = response.get("choices") or []
            if not choices:
                self.finished_signal.emit(False, None, "Story planning returned no choices.")
                return

            message = choices[0].get("message") or {}
            content = message.get("content")
            if isinstance(content, list):
                content = "".join(
                    item.get("text", "")
                    for item in content
                    if isinstance(item, dict)
                )

            plan = parse_comic_plan(content, self.page_count)
            self.finished_signal.emit(True, plan, "")
        except Exception as e:
            self.finished_signal.emit(False, None, str(e))
