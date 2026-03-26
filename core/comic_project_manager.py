import json
import os
import re
import shutil
from datetime import datetime

from core.config import cfg


PROJECT_FILE_NAME = "project.json"


def _normalize_project_name(name):
    cleaned = re.sub(r'[<>:"/\\|?*]+', "_", (name or "").strip())
    cleaned = re.sub(r"\s+", "_", cleaned)
    return cleaned.strip("._")


class ComicProjectManager:
    def projects_root(self):
        root = cfg.get("output_folder")
        os.makedirs(root, exist_ok=True)
        return root

    def legacy_projects_root(self):
        return os.path.join(self.projects_root(), "projects")

    def project_dir(self, project_name):
        normalized = _normalize_project_name(project_name)
        if not normalized:
            raise ValueError("Project name is empty.")
        path = os.path.join(self.projects_root(), normalized)
        return normalized, path

    def project_file(self, project_name):
        _, root = self.project_dir(project_name)
        return os.path.join(root, PROJECT_FILE_NAME)

    def list_projects(self):
        names = []
        for root in [self.projects_root(), self.legacy_projects_root()]:
            if not os.path.isdir(root):
                continue
            for entry in os.listdir(root):
                full_path = os.path.join(root, entry)
                if os.path.isdir(full_path) and os.path.exists(os.path.join(full_path, PROJECT_FILE_NAME)):
                    names.append(entry)
        return sorted(set(names), reverse=True)

    def _copy_reference_images(self, project_root, ref_paths):
        refs_dir = os.path.join(project_root, "reference_images")
        os.makedirs(refs_dir, exist_ok=True)

        copied_refs = []
        for index, ref_path in enumerate(ref_paths or [], start=1):
            if not ref_path or not os.path.isfile(ref_path):
                continue
            ext = os.path.splitext(ref_path)[1].lower() or ".png"
            target_name = f"ref_{index:02d}{ext}"
            target_path = os.path.join(refs_dir, target_name)
            try:
                if os.path.abspath(ref_path) != os.path.abspath(target_path):
                    shutil.copy2(ref_path, target_path)
            except Exception:
                continue

            copied_refs.append(
                {
                    "source_path": ref_path,
                    "project_relative_path": os.path.relpath(target_path, project_root),
                }
            )
        return copied_refs

    def save_project(self, project_name, payload):
        normalized_name, project_root = self.project_dir(project_name)
        pages_dir = os.path.join(project_root, "pages")
        os.makedirs(project_root, exist_ok=True)
        os.makedirs(pages_dir, exist_ok=True)

        reference_images = self._copy_reference_images(project_root, payload.get("reference_images"))
        project_payload = {
            "project_name": normalized_name,
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "story_requirement": payload.get("story_requirement", ""),
            "style_notes": payload.get("style_notes", ""),
            "plan_title": payload.get("plan_title", ""),
            "plan_style_notes": payload.get("plan_style_notes", ""),
            "settings": payload.get("settings", {}),
            "pages": payload.get("pages", []),
            "reference_images": reference_images,
            "generated_outputs": payload.get("generated_outputs", {}),
            "pages_directory": pages_dir,
        }

        with open(os.path.join(project_root, PROJECT_FILE_NAME), "w", encoding="utf-8") as f:
            json.dump(project_payload, f, ensure_ascii=False, indent=2)

        return {
            "project_name": normalized_name,
            "project_root": project_root,
            "pages_dir": pages_dir,
            "project_file": os.path.join(project_root, PROJECT_FILE_NAME),
            "payload": project_payload,
        }

    def load_project(self, project_name):
        normalized_name, project_root = self.project_dir(project_name)
        project_file = os.path.join(project_root, PROJECT_FILE_NAME)
        if not os.path.exists(project_file):
            legacy_root = os.path.join(self.legacy_projects_root(), normalized_name)
            legacy_file = os.path.join(legacy_root, PROJECT_FILE_NAME)
            if os.path.exists(legacy_file):
                project_root = legacy_root
                project_file = legacy_file
            else:
                raise FileNotFoundError(f"Project file not found: {project_file}")

        with open(project_file, "r", encoding="utf-8") as f:
            payload = json.load(f)

        resolved_reference_images = []
        for ref in payload.get("reference_images", []):
            if not isinstance(ref, dict):
                continue
            project_relative_path = ref.get("project_relative_path")
            source_path = ref.get("source_path")
            project_copy = os.path.join(project_root, project_relative_path) if project_relative_path else ""
            if project_relative_path and os.path.exists(project_copy):
                resolved_reference_images.append(project_copy)
            elif source_path and os.path.exists(source_path):
                resolved_reference_images.append(source_path)

        payload["resolved_reference_images"] = resolved_reference_images
        payload["project_root"] = project_root
        payload["project_file"] = project_file
        payload["pages_dir"] = payload.get("pages_directory") or os.path.join(project_root, "pages")
        payload["project_name"] = normalized_name
        return payload


project_manager = ComicProjectManager()
