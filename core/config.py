import json
import os

CONFIG_FILE = 'config.json'

DEFAULT_CONFIG = {
    "api_base_url": "https://grsai.dakka.com.cn",
    "api_key": "",
    "output_folder": os.path.join(os.getcwd(), "output"),
    "last_model": "nano-banana-fast",
    "last_aspect_ratio": "auto",
    "last_image_size": "1K",
    "max_retries": 5,
    "theme": "auto",
    "text_format_enabled": True,
    "text_font_size": 12,
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
                return json.load(f)
        except:
            return DEFAULT_CONFIG

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
