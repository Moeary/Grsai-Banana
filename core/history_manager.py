import json
import os
from datetime import datetime

HISTORY_FILE = 'history.json'

class HistoryManager:
    def __init__(self):
        self.history = self.load_history()

    def load_history(self):
        if not os.path.exists(HISTORY_FILE):
            return []
        try:
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return []

    def save_history(self):
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.history, f, indent=4, ensure_ascii=False)

    def add_task(self, task_id, prompt, model, aspect_ratio, image_size, ref_images=None):
        task = {
            "id": task_id,
            "prompt": prompt,
            "model": model,
            "aspect_ratio": aspect_ratio,
            "image_size": image_size,
            "ref_images": ref_images,
            "status": "running",
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "result_path": None,
            "preview_url": None
        }
        self.history.insert(0, task) # Add to top
        self.save_history()
        return task

    def update_task(self, task_id, status, result_path=None, preview_url=None, failure_reason=None):
        for task in self.history:
            if task["id"] == task_id:
                task["status"] = status
                if result_path:
                    task["result_path"] = result_path
                if preview_url:
                    task["preview_url"] = preview_url
                if failure_reason:
                    task["failure_reason"] = failure_reason
                self.save_history()
                return task
        return None

    def get_all_tasks(self):
        return self.history

history_mgr = HistoryManager()
