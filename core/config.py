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
    "vip_moderation_auto_retry": False,
    "parallel_tasks": 1,
    "max_retries": 5,
    "theme": "auto",
    "language": "en",
    "text_format_enabled": True,
    "text_font_size": 12,
    "text_font_family": "Arial",
    "text_auto_wrap": True,
    # History page settings
    "history_items_per_page": 5,
    "last_tab": "banana_1"
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

        # Migrate old Google Gemini setup to Grsai Nano Banana
        if migrated.get("api_base_url", "").startswith("https://generativelanguage.googleapis.com"):
            migrated["api_base_url"] = DEFAULT_CONFIG["api_base_url"]

        legacy_model_map = {
            "gemini-2.5-flash-image": "nano-banana-fast"
        }
        last_model = migrated.get("last_model")
        if last_model in legacy_model_map:
            migrated["last_model"] = legacy_model_map[last_model]

        for key, value in list(migrated.items()):
            if key.startswith("last_model_") and value in legacy_model_map:
                migrated[key] = legacy_model_map[value]

        # Migrate old tab names to stable tab keys used by i18n
        tab_key_map = {
            "Banana 1": "banana_1",
            "Banana Pro": "banana_pro",
            "GPT Image": "gpt_image",
        }
        old_last_tab = migrated.get("last_tab")
        if old_last_tab in tab_key_map:
            migrated["last_tab"] = tab_key_map[old_last_tab]

        for old_name, new_key in tab_key_map.items():
            old_model_key = f"last_model_{old_name}"
            new_model_key = f"last_model_tab_{new_key}"
            if old_model_key in migrated and new_model_key not in migrated:
                migrated[new_model_key] = migrated[old_model_key]
        
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
