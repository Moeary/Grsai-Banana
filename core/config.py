import json
import os

CONFIG_FILE = 'config.json'

DEFAULT_CONFIG = {
    "api_base_url": "https://grsai.dakka.com.cn",
    "api_key": "",
    "output_folder": os.path.join(os.getcwd(), "output"),
    "last_model": "nano-banana-fast",
    # Nano Banana parameters
    "nano_banana_aspect_ratio": "auto",
    "nano_banana_image_size": "1K",
    # GPT Image / Sora parameters
    "gpt_image_size": "auto",
    # Shared parameters
    "auto_retry_on_failure": False,
    "parallel_tasks": 1,
    "max_retries": 5,
    "theme": "auto",
    "text_format_enabled": True,
    "text_font_size": 12,
    "text_font_family": "Arial",
    "text_auto_wrap": True
}

class Config:
    def __init__(self):
        self.data = self.load_config()

    def load_config(self):
        if not os.path.exists(CONFIG_FILE):
            self.save_config(DEFAULT_CONFIG)
            return DEFAULT_CONFIG
        
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                loaded = json.load(f)
                # Migrate old config format to new one
                loaded = self._migrate_config(loaded)
                return loaded
        except:
            return DEFAULT_CONFIG
    
    def _migrate_config(self, old_config):
        """Migrate old config format to new one"""
        migrated = old_config.copy()
        
        # Migrate old last_aspect_ratio and last_image_size to nano_banana_*
        if "last_aspect_ratio" in migrated:
            migrated["nano_banana_aspect_ratio"] = migrated.pop("last_aspect_ratio", "auto")
        if "last_image_size" in migrated:
            migrated["nano_banana_image_size"] = migrated.pop("last_image_size", "1K")
        
        # Ensure all required keys exist
        for key, value in DEFAULT_CONFIG.items():
            if key not in migrated:
                migrated[key] = value
        
        return migrated

    def save_config(self, data=None):
        if data is None:
            data = self.data
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

    def get(self, key, default=None):
        return self.data.get(key, default)

    def set(self, key, value):
        self.data[key] = value
        self.save_config()

cfg = Config()
