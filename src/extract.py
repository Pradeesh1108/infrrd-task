import sys
import json
from pathlib import Path
import warnings
from urllib3.exceptions import InsecureRequestWarning

warnings.simplefilter('ignore', InsecureRequestWarning)

# Add repo root to sys.path so we can import our modules
repo_root = Path(__file__).parent.parent
sys.path.insert(0, str(repo_root))

from src.ollama_client import call_llm_with_retry
from src.prompts import build_extraction_prompt

class ExtractionError(Exception):
    pass


def _extract_text_block(text: str, fields: list[str]) -> dict:
    result = {}
    for f in fields:
        result[f] = {"value": None, "confidence": 0.0, "parse_error": "Missing from output"}
        
    lines = text.strip().split('\n')
    current_field = None
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        import re
        conf_match = re.match(r'^confidence\s*:\s*(.+)$', line, re.IGNORECASE)
        if conf_match:
            if current_field and current_field in result:
                try:
                    result[current_field]["confidence"] = float(conf_match.group(1).strip())
                    result[current_field].pop("parse_error", None)
                except ValueError:
                    pass
            current_field = None
            continue
            
        if ":" in line:
            parts = line.split(":", 1)
            key = parts[0].strip()
            val = parts[1].strip()
            
            if key in result:
                current_field = key
                if val.lower() == "null" or val == "":
                    result[key]["value"] = None
                else:
                    result[key]["value"] = val
                    
    return result

def extract_fields(
    ocr_text: str,
    doc_type: str,
    fields: list[str],
    image_path: str = None,
    model: str = "llama3.1",
) -> dict:
    
    prompt = build_extraction_prompt(doc_type, fields, ocr_text)
    raw_output = call_llm_with_retry(prompt, image_path=image_path, model=model, max_retries=6)
    
    return _extract_text_block(raw_output, fields)
