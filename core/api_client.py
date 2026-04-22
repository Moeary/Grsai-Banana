import requests
import json
import os
import base64
from core.config import cfg
from core.model_catalog import (
    NANO_MODELS,
    NANO_IMAGE_SIZE_OPTIONS,
    COMPLETION_MODELS,
    LEGACY_IMAGE_MODEL_ALIASES,
)

class ApiClient:
    LEGACY_MODEL_ALIASES = {
        "gemini-2.5-flash-image": "nano-banana-fast",
        **LEGACY_IMAGE_MODEL_ALIASES,
    }
    LEGACY_COMPLETION_MODELS = {"sora-2", "veo3.1-fast-1080p"}
    def __init__(self):
        pass

    def get_headers(self):
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {cfg.get('api_key')}"
        }

    def _get_base_url(self):
        base_url = cfg.get("api_base_url", "").strip()
        return base_url or "https://grsai.dakka.com.cn"

    def _normalize_model(self, model):
        return self.LEGACY_MODEL_ALIASES.get(model, model)

    def _convert_image_to_data_uri(self, image_path):
        """Convert local image file to data URI for API submission"""
        try:
            if os.path.isfile(image_path):
                with open(image_path, "rb") as f:
                    b64_string = base64.b64encode(f.read()).decode('utf-8')
                    ext = os.path.splitext(image_path)[1].lower().replace('.', '')
                    if ext == 'jpg': ext = 'jpeg'
                    return f"data:image/{ext};base64,{b64_string}"
        except Exception as e:
            print(f"Error converting image to data URI: {e}")
        return None

    def _normalize_chat_messages(self, messages):
        normalized = []
        for message in messages or []:
            if not isinstance(message, dict):
                normalized.append(message)
                continue

            normalized_message = dict(message)
            content = normalized_message.get("content")
            if isinstance(content, list):
                normalized_content = []
                for item in content:
                    if not isinstance(item, dict):
                        normalized_content.append(item)
                        continue

                    normalized_item = dict(item)
                    if item.get("type") == "image_url":
                        image_url = item.get("image_url")
                        if isinstance(image_url, dict):
                            url = image_url.get("url")
                            if isinstance(url, str) and os.path.isfile(url):
                                data_uri = self._convert_image_to_data_uri(url)
                                if data_uri:
                                    normalized_item["image_url"] = dict(image_url)
                                    normalized_item["image_url"]["url"] = data_uri
                        elif isinstance(image_url, str) and os.path.isfile(image_url):
                            data_uri = self._convert_image_to_data_uri(image_url)
                            if data_uri:
                                normalized_item["image_url"] = {"url": data_uri}
                    normalized_content.append(normalized_item)
                normalized_message["content"] = normalized_content
            normalized.append(normalized_message)
        return normalized

    def chat_completion(self, model, messages, stream=False, temperature=None):
        """Call OpenAI-compatible chat completions API."""
        url = f"{self._get_base_url().rstrip('/')}/v1/chat/completions"
        payload = {
            "model": model,
            "stream": stream,
            "messages": self._normalize_chat_messages(messages),
        }

        if temperature is not None:
            payload["temperature"] = temperature

        try:
            response = requests.post(url, headers=self.get_headers(), json=payload, timeout=120)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": {"message": str(e)}}
        except Exception as e:
            return {"error": {"message": str(e)}}

    def submit_task(self, prompt, model, aspect_ratio="auto", image_size="1K", ref_image_urls=None, variants=1):
        """Submit task to appropriate API based on model"""
        model = self._normalize_model(model)

        # Convert local file paths to data URIs for API submission
        if ref_image_urls:
            converted_urls = []
            for url in ref_image_urls:
                if os.path.isfile(url):  # It's a local file path
                    data_uri = self._convert_image_to_data_uri(url)
                    if data_uri:
                        converted_urls.append(data_uri)
                else:  # It's already a URL or data URI
                    converted_urls.append(url)
            ref_image_urls = converted_urls if converted_urls else None
        
        # Determine which API to use
        if model in NANO_MODELS:
            return self._submit_nano_banana(prompt, model, aspect_ratio, image_size, ref_image_urls)
        elif model in COMPLETION_MODELS or model in self.LEGACY_COMPLETION_MODELS:
            return self._submit_gpt_image(prompt, model, image_size, ref_image_urls, variants)
        else:
            return {"code": -1, "msg": f"Unknown model: {model}"}

    def _submit_nano_banana(self, prompt, model, aspect_ratio, image_size, ref_image_urls):
        """Submit to Nano Banana API"""
        url = f"{self._get_base_url().rstrip('/')}/v1/draw/nano-banana"
        
        payload = {
            "model": model,
            "prompt": prompt,
            "aspectRatio": aspect_ratio,
            "webHook": "-1",  # Use -1 to get ID immediately for polling
            "shutProgress": False
        }

        if model in NANO_IMAGE_SIZE_OPTIONS:
            payload["imageSize"] = image_size

        if ref_image_urls:
            payload["urls"] = ref_image_urls

        try:
            response = requests.post(url, headers=self.get_headers(), json=payload, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"code": -1, "msg": str(e)}

    def _submit_gpt_image(self, prompt, model, size, ref_image_urls, variants):
        """Submit to GPT Image API"""
        url = f"{self._get_base_url().rstrip('/')}/v1/draw/completions"
        
        payload = {
            "model": model,
            "prompt": prompt,
            "size": size if size in ["auto", "1:1", "3:2", "2:3"] else "1:1",
            "variants": variants,
            "webHook": "-1",  # Use -1 to get ID immediately for polling
            "shutProgress": False
        }

        if ref_image_urls:
            payload["urls"] = ref_image_urls

        try:
            response = requests.post(url, headers=self.get_headers(), json=payload, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"code": -1, "msg": str(e)}

    def get_task_result(self, task_id):
        """Get task result - works for both APIs"""
        url = f"{self._get_base_url().rstrip('/')}/v1/draw/result"
        payload = {"id": task_id}

        try:
            response = requests.post(url, headers=self.get_headers(), json=payload, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"code": -1, "msg": str(e)}

api = ApiClient()
