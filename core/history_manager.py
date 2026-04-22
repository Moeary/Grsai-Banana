import json
import os
import sqlite3
import threading
from datetime import datetime

HISTORY_DB_FILE = "history.db"
LEGACY_HISTORY_FILE = "history.json"


class HistoryManager:
    def __init__(self):
        self._lock = threading.RLock()
        self._ensure_db()
        self._migrate_legacy_json()

    def _connect(self):
        conn = sqlite3.connect(HISTORY_DB_FILE, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_db(self):
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS history_tasks (
                    id TEXT PRIMARY KEY,
                    prompt TEXT NOT NULL,
                    model TEXT NOT NULL,
                    aspect_ratio TEXT NOT NULL,
                    image_size TEXT NOT NULL,
                    ref_images TEXT,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    result_path TEXT,
                    preview_url TEXT,
                    failure_reason TEXT,
                    error_message TEXT,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_history_created_at ON history_tasks(created_at DESC)"
            )
            conn.commit()

    def _serialize_ref_images(self, ref_images):
        if ref_images is None:
            return None
        try:
            return json.dumps(ref_images, ensure_ascii=False)
        except Exception:
            return None

    def _deserialize_ref_images(self, value):
        if not value:
            return None
        try:
            return json.loads(value)
        except Exception:
            return None

    def _row_to_task(self, row):
        task = dict(row)
        task["ref_images"] = self._deserialize_ref_images(task.get("ref_images"))
        return task

    def _insert_task(self, conn, task):
        conn.execute(
            """
            INSERT OR REPLACE INTO history_tasks (
                id, prompt, model, aspect_ratio, image_size, ref_images,
                status, created_at, result_path, preview_url,
                failure_reason, error_message, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                task["id"],
                task["prompt"],
                task["model"],
                task["aspect_ratio"],
                task["image_size"],
                self._serialize_ref_images(task.get("ref_images")),
                task["status"],
                task["created_at"],
                task.get("result_path"),
                task.get("preview_url"),
                task.get("failure_reason"),
                task.get("error_message"),
                task.get("updated_at") or datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            ),
        )

    def _migrate_legacy_json(self):
        if not os.path.exists(LEGACY_HISTORY_FILE):
            return
        try:
            with open(LEGACY_HISTORY_FILE, "r", encoding="utf-8") as f:
                legacy_tasks = json.load(f)
        except Exception:
            legacy_tasks = []

        if not isinstance(legacy_tasks, list) or not legacy_tasks:
            return

        with self._lock:
            with self._connect() as conn:
                for task in legacy_tasks:
                    if not isinstance(task, dict) or not task.get("id"):
                        continue
                    normalized = {
                        "id": task.get("id"),
                        "prompt": task.get("prompt", ""),
                        "model": task.get("model", ""),
                        "aspect_ratio": task.get("aspect_ratio", "auto"),
                        "image_size": task.get("image_size", "1K"),
                        "ref_images": task.get("ref_images"),
                        "status": task.get("status", "running"),
                        "created_at": task.get("created_at") or datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "result_path": task.get("result_path"),
                        "preview_url": task.get("preview_url"),
                        "failure_reason": task.get("failure_reason"),
                        "error_message": task.get("error_message"),
                        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    }
                    self._insert_task(conn, normalized)
                conn.commit()

        try:
            backup_file = f"{LEGACY_HISTORY_FILE}.bak"
            if os.path.exists(backup_file):
                os.remove(backup_file)
            os.replace(LEGACY_HISTORY_FILE, backup_file)
        except Exception:
            pass

    def add_task(self, task_id, prompt, model, aspect_ratio, image_size, ref_images=None):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        task = {
            "id": task_id,
            "prompt": prompt,
            "model": model,
            "aspect_ratio": aspect_ratio,
            "image_size": image_size,
            "ref_images": ref_images,
            "status": "running",
            "created_at": now,
            "result_path": None,
            "preview_url": None,
            "failure_reason": None,
            "error_message": None,
            "updated_at": now,
        }
        with self._lock:
            with self._connect() as conn:
                self._insert_task(conn, task)
                conn.commit()
        return task

    def update_task(self, task_id, status, result_path=None, preview_url=None, failure_reason=None, error_message=None):
        fields = {
            "status": status,
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        if result_path:
            fields["result_path"] = result_path
        if preview_url:
            fields["preview_url"] = preview_url
        if failure_reason:
            fields["failure_reason"] = failure_reason
        if error_message:
            fields["error_message"] = error_message

        set_clause = ", ".join([f"{k} = ?" for k in fields.keys()])
        params = list(fields.values()) + [task_id]

        with self._lock:
            with self._connect() as conn:
                conn.execute(f"UPDATE history_tasks SET {set_clause} WHERE id = ?", params)
                conn.commit()
                row = conn.execute("SELECT * FROM history_tasks WHERE id = ?", (task_id,)).fetchone()
                if row is None:
                    return None
                return self._row_to_task(row)

    def get_all_tasks(self):
        with self._lock:
            with self._connect() as conn:
                rows = conn.execute("SELECT * FROM history_tasks ORDER BY created_at DESC, id DESC").fetchall()
        return [self._row_to_task(row) for row in rows]

    def get_task_count(self):
        with self._lock:
            with self._connect() as conn:
                row = conn.execute("SELECT COUNT(1) AS cnt FROM history_tasks").fetchone()
                return int(row["cnt"] if row else 0)

    def clear_all_tasks(self):
        with self._lock:
            with self._connect() as conn:
                row = conn.execute("SELECT COUNT(1) AS cnt FROM history_tasks").fetchone()
                deleted_count = int(row["cnt"] if row else 0)
                conn.execute("DELETE FROM history_tasks")
                conn.commit()
                conn.execute("VACUUM")
        return deleted_count

    def clear_failed_tasks(self):
        with self._lock:
            with self._connect() as conn:
                cursor = conn.execute("DELETE FROM history_tasks WHERE status = ?", ("failed",))
                deleted_count = cursor.rowcount if cursor.rowcount is not None else 0
                conn.commit()
                conn.execute("VACUUM")
        return max(int(deleted_count), 0)

    def clear_running_tasks(self):
        with self._lock:
            with self._connect() as conn:
                cursor = conn.execute("DELETE FROM history_tasks WHERE status = ?", ("running",))
                deleted_count = cursor.rowcount if cursor.rowcount is not None else 0
                conn.commit()
                conn.execute("VACUUM")
        return max(int(deleted_count), 0)

    def get_tasks_page(self, page, page_size):
        safe_page = max(int(page), 1)
        safe_page_size = max(int(page_size), 1)
        offset = (safe_page - 1) * safe_page_size
        with self._lock:
            with self._connect() as conn:
                rows = conn.execute(
                    """
                    SELECT * FROM history_tasks
                    ORDER BY created_at DESC, id DESC
                    LIMIT ? OFFSET ?
                    """,
                    (safe_page_size, offset),
                ).fetchall()
        return [self._row_to_task(row) for row in rows]


history_mgr = HistoryManager()
