import requests
import json
import os
import base64
from core.config import cfg

class ApiClient:
    def __init__(self):
        pass

    def get_headers(self):
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {cfg.get('api_key')}"
        }

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

    def submit_task(self, prompt, model, aspect_ratio="auto", image_size="1K", ref_image_urls=None, variants=1):
        """Submit task to appropriate API based on model"""
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
        if model.startswith("nano-banana"):
            return self._submit_nano_banana(prompt, model, aspect_ratio, image_size, ref_image_urls)
        elif model in ["gpt-image-1.5", "sora-image"]:
            return self._submit_gpt_image(prompt, model, aspect_ratio, ref_image_urls, variants)
        else:
            return {"code": -1, "msg": f"Unknown model: {model}"}

    def _submit_nano_banana(self, prompt, model, aspect_ratio, image_size, ref_image_urls):
        """Submit to Nano Banana API"""
        url = f"{cfg.get('api_base_url').rstrip('/')}/v1/draw/nano-banana"
        
        payload = {
            "model": model,
            "prompt": prompt,
            "aspectRatio": aspect_ratio,
            "imageSize": image_size,
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

    def _submit_gpt_image(self, prompt, model, size, ref_image_urls, variants):
        """Submit to GPT Image / Sora API"""
        url = f"{cfg.get('api_base_url').rstrip('/')}/v1/draw/completions"
        
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
        url = f"{cfg.get('api_base_url').rstrip('/')}/v1/draw/result"
        payload = {"id": task_id}

        try:
            response = requests.post(url, headers=self.get_headers(), json=payload, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"code": -1, "msg": str(e)}

api = ApiClient()
