import os
import time
import requests
from src.llm_factory import factory

DEFAULT_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.1")
DEFAULT_TIMEOUT = 600

def call_llm(
    prompt: str,
    image_path: str = None,
    model: str = DEFAULT_MODEL,
    temperature: float = 0.0,
    timeout: int = DEFAULT_TIMEOUT,
) -> str:
    return factory.call_llm(prompt, image_path, model, temperature, timeout)

def call_llm_with_retry(
    prompt: str,
    image_path: str = None,
    model: str = DEFAULT_MODEL,
    max_retries: int = 6,
    backoff_seconds: float = 5.0,
    **kwargs,
) -> str:
    last_exc = None
    attempt = 1
    while True:
        try:
            return call_llm(prompt, image_path=image_path, model=model, **kwargs)
        except Exception as exc:
            last_exc = exc
            is_429 = getattr(exc, 'response', None) is not None and exc.response.status_code == 429
            if attempt < max_retries or is_429:
                sleep_time = backoff_seconds * min(attempt, 10)
                if is_429:
                    sleep_time = 20.0 * min(attempt, 5) # Max 100s sleep
                print(f'API Error (Attempt {attempt}): {exc}. Retrying in {sleep_time}s...', flush=True)
                time.sleep(sleep_time)
                attempt += 1
            else:
                break
    raise RuntimeError(f"LLM call failed after {attempt - 1} attempts") from last_exc
