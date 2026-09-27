import os
import time
import threading
import base64
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

class LLMFactory:
    def __init__(self):
        self.provider = os.environ.get("LLM_PROVIDER", "groq").lower()
        self.ngrok_url = os.environ.get("NGROK_BASE_URL", "http://localhost:11434")
        
        self.groq_keys = []
        for i in range(1, 5):
            k = os.environ.get(f"test{i}")
            if k:
                self.groq_keys.append(k)
                
        self.key_usage = {k: [] for k in self.groq_keys}
        self.lock = threading.Lock()
        
    def _encode_image(self, image_path: str) -> str:
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')

    def _get_groq_key(self):
        while True:
            with self.lock:
                now = time.time()
                for k in self.groq_keys:
                    # Filter timestamps older than 60s
                    self.key_usage[k] = [ts for ts in self.key_usage[k] if now - ts < 60.5]
                    # Allow 1 call per minute per key to avoid Groq 7000 TPM limit on vision models
                    if len(self.key_usage[k]) < 1:
                        self.key_usage[k].append(now)
                        return k
            time.sleep(2) # Sleep to avoid spamming the lock

    def call_llm(self, prompt: str, image_path: str, model: str, temperature: float, timeout: int) -> str:
        if self.provider == "groq" and self.groq_keys:
            return self._call_groq(prompt, image_path, "qwen/qwen3.8-27b", temperature, timeout)
        else:
            return self._call_ollama(prompt, image_path, model, temperature, timeout)

    def _call_groq(self, prompt: str, image_path: str, model: str, temperature: float, timeout: int) -> str:
        key = self._get_groq_key()
        
        # Groq expects OpenAI format
        content = [{"type": "text", "text": prompt}]
        if image_path:
            b64 = self._encode_image(image_path)
            content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{b64}"}
            })
            
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": content}],
            "temperature": temperature,
        }
        
        resp = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            json=payload,
            headers={"Authorization": f"Bearer {key}"},
            timeout=timeout
        )
        if resp.status_code == 429:
            # We hit a rate limit somehow, raise and retry
            resp.raise_for_status()
        
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]

    def _call_ollama(self, prompt: str, image_path: str, model: str, temperature: float, timeout: int) -> str:
        url = self.ngrok_url
        if not url.startswith("http"):
            url = f"http://{url}"
            
        msg = {"role": "user", "content": prompt}
        if image_path:
            msg["images"] = [self._encode_image(image_path)]
            
        payload = {
            "model": model,
            "messages": [msg],
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_ctx": 8192
            }
        }
        resp = requests.post(
            f"{url}/api/chat",
            json=payload,
            timeout=timeout,
        )
        resp.raise_for_status()
        return resp.json()["message"]["content"]

factory = LLMFactory()
