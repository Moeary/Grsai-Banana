"""
Task Manager - Handles all task-related logic independently from UI
"""
import os
import time
import requests
from datetime import datetime
from PySide6.QtCore import QThread, Signal

from core.config import cfg
from core.api_client import api
from core.history_manager import history_mgr


class TaskWorker(QThread):
    """Worker thread for submitting and polling tasks"""
    progress_signal = Signal(int, str)
    finished_signal = Signal(bool, str, str)  # success, result_path/msg, failure_reason
    
    def __init__(self, prompt, model, ratio, size, ref_urls, task_id=None):
        super().__init__()
        self.prompt = prompt
        self.model = model
        self.ratio = ratio
        self.size = size
        self.ref_urls = ref_urls
        self.task_id = task_id
        self.is_running = True
        self.setTerminationEnabled(True)

    def run(self):
        try:
            if not self.task_id:
                try:
                    res = api.submit_task(self.prompt, self.model, self.ratio, self.size, self.ref_urls)
                    if res.get("code") != 0:
                        self.finished_signal.emit(False, res.get("msg", "Submission failed"), "Submission failed")
                        return
                    self.task_id = res["data"]["id"]
                    # Add to history
                    history_mgr.add_task(
                        self.task_id, 
                        self.prompt, 
                        self.model,
                        self.ratio,
                        self.size,
                        self.ref_urls
                    )
                except Exception as e:
                    print(f"[TaskWorker] Submission error: {e}")
                    self.finished_signal.emit(False, str(e), "Submission Exception")
                    return

            error_count = 0
            while self.is_running:
                # Check stop flag at loop start
                if not self.is_running:
                    return
                    
                try:
                    res = api.get_task_result(self.task_id)
                    error_count = 0
                except Exception as e:
                    error_count += 1
                    print(f"[TaskWorker] API call error (attempt {error_count}): {e}")
                    if error_count > 5:
                        self.finished_signal.emit(False, f"Network error: {str(e)}", "Network Error")
                        return
                    # Sleep in shorter intervals to respond to stop signals quickly
                    for _ in range(4):
                        if not self.is_running:
                            return
                        time.sleep(0.5)
                    continue

                try:
                    if res.get("code") != 0:
                        if res.get("code") == -22:
                            # Task not ready yet, sleep in shorter intervals
                            for _ in range(4):
                                if not self.is_running:
                                    return
                                time.sleep(0.5)
                            continue
                        self.finished_signal.emit(False, res.get("msg", "Unknown error"), "API Error")
                        return

                    data = res.get("data", {})
                    status = data.get("status")
                    progress = data.get("progress", 0)
                    
                    if not self.is_running:
                        return
                    
                    self.progress_signal.emit(progress, status)

                    if status == "succeeded":
                        results = data.get("results", [])
                        if results:
                            img_url = results[0].get("url")
                            try:
                                img_data = requests.get(img_url, timeout=30).content
                                timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
                                ext = "png"
                                if ".jpg" in img_url: ext = "jpg"
                                if ".jpeg" in img_url: ext = "jpeg"
                                
                                filename = f"{timestamp}.{ext}"
                                output_dir = cfg.get("output_folder")
                                if not os.path.exists(output_dir):
                                    os.makedirs(output_dir)
                                    
                                filepath = os.path.join(output_dir, filename)
                                with open(filepath, "wb") as f:
                                    f.write(img_data)
                                    
                                history_mgr.update_task(self.task_id, "succeeded", result_path=filepath, preview_url=img_url)
                                self.finished_signal.emit(True, filepath, "Success")
                            except Exception as e:
                                print(f"[TaskWorker] Download error: {e}")
                                history_mgr.update_task(self.task_id, "failed", failure_reason=str(e))
                                self.finished_signal.emit(False, str(e), "Download Failed")
                        else:
                            history_mgr.update_task(self.task_id, "failed", failure_reason="No results found")
                            self.finished_signal.emit(False, "No results found", "No Results")
                        return

                    elif status == "failed":
                        reason = data.get("failure_reason", "Unknown")
                        error_msg = data.get("error", "")
                        history_mgr.update_task(self.task_id, "failed", failure_reason=reason, error_message=error_msg)
                        self.finished_signal.emit(False, reason, reason)
                        return
                except Exception as e:
                    print(f"[TaskWorker] Processing error: {e}")
                    self.finished_signal.emit(False, str(e), "Processing Error")
                    return

                # Sleep in shorter intervals to respond to stop signals quickly
                for _ in range(4):
                    if not self.is_running:
                        return
                    time.sleep(0.5)
        except Exception as e:
            print(f"[TaskWorker] Unexpected error in run(): {e}")
            try:
                self.finished_signal.emit(False, str(e), "Unexpected Error")
            except:
                pass
            
    def stop(self):
        self.is_running = False


class TaskManager:
    """Manages all active tasks and workers"""
    
    def __init__(self):
        self.active_workers = {}  # task_widget -> worker
    
    def create_worker(self, prompt, model, ratio, size, ref_urls):
        """Create and return a new TaskWorker"""
        worker = TaskWorker(prompt, model, ratio, size, ref_urls)
        return worker
    
    def stop_worker(self, task_widget):
        """Stop a specific worker"""
        if task_widget in self.active_workers:
            worker = self.active_workers[task_widget]
            worker.stop()
            worker.deleteLater()
    
    def register_worker(self, task_widget, worker):
        """Register a worker for a task"""
        # Stop existing worker if any
        if task_widget in self.active_workers:
            old_worker = self.active_workers[task_widget]
            old_worker.stop()
            old_worker.deleteLater()
        
        self.active_workers[task_widget] = worker
    
    def unregister_worker(self, task_widget):
        """Unregister a worker"""
        if task_widget in self.active_workers:
            del self.active_workers[task_widget]
    
    def stop_all_workers(self):
        """Stop all active workers"""
        print(f"[TaskManager] Stopping {len(self.active_workers)} worker thread(s)...")
        try:
            # Signal all workers to stop
            for worker in list(self.active_workers.values()):
                try:
                    worker.stop()
                except Exception as e:
                    print(f"[TaskManager] Error stopping worker: {e}")
            
            # Wait for all workers to finish with a timeout
            for i, worker in enumerate(list(self.active_workers.values())):
                try:
                    if not worker.wait(3000):  # Wait max 3 seconds per thread
                        print(f"[TaskManager] Worker {i} timeout during wait")
                except Exception as e:
                    print(f"[TaskManager] Error waiting for worker: {e}")
            
            self.active_workers.clear()
            print("[TaskManager] All workers stopped")
        except Exception as e:
            print(f"[TaskManager] Error in stop_all_workers: {e}")


# Global task manager instance
task_manager = TaskManager()
