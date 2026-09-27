"""Orchestrates the full pipeline for a manifest (dev or test):
  for each image -> OCR -> extract fields (cached) -> decide predictions -> write JSON

Usage:
  python -m src.run_pipeline --manifest dev/manifest.json --images dev \
      --out outputs/dev_predictions.json
"""
import argparse
import json
import sys
import time
from pathlib import Path

repo_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo_root))

from src.extract import extract_fields, ExtractionError
from src.abstain import decide_predictions
from src.layout import get_parser

CACHE_DIR = repo_root / "cache" / "raw"


def _cache_path(image_id: str) -> Path:
    return CACHE_DIR / f"{image_id}.json"


def _load_cached(image_id: str) -> dict | None:
    path = _cache_path(image_id)
    if path.exists():
        return json.loads(path.read_text())
    return None


def _save_cache(image_id: str, extracted: dict) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    _cache_path(image_id).write_text(json.dumps(extracted, indent=2))


def process_image(
    image_id: str,
    image_file: str,
    images_root: str,
    doc_type: str,
    fields: list[str],
    use_cache: bool = True,
    model: str = "llama3.1",
) -> dict:
    if use_cache:
        cached = _load_cached(image_id)
        if cached is not None:
            return cached

    full_path = Path(images_root) / image_file
    if not full_path.exists():
        full_path = Path(images_root) / Path(image_file).name
    if not full_path.exists():
        full_path = Path(image_file)

    try:
        parser = get_parser()
        ocr_text = parser.parse(str(full_path))
        extracted = extract_fields(ocr_text, doc_type, fields, image_path=str(full_path), model=model)
    except Exception as exc:
        extracted = {f: {"value": None, "confidence": 0.0, "error": str(exc)} for f in fields}

    _save_cache(image_id, extracted)
    return extracted


def run(manifest_path: str, images_root: str, out_path: str, threshold: float = 0.5,
        use_cache: bool = True, model: str = "llama3.1") -> None:
    manifest = json.loads(Path(manifest_path).read_text())
    images = manifest["images"]

    all_predictions = {}
    all_debug = {}

    import concurrent.futures
    import threading

    total = len(images)
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    debug_out = out.with_name(out.stem + "_debug.json")
    
    write_lock = threading.Lock()

    def _save_state():
        with write_lock:
            sorted_preds = dict(sorted(all_predictions.items()))
            sorted_debug = dict(sorted(all_debug.items()))
            out.write_text(json.dumps(sorted_preds, indent=2))
            debug_out.write_text(json.dumps(sorted_debug, indent=2))

    def _process_wrapper(i, entry):
        image_id = entry["id"]
        print(f"[{i}/{total}] STARTING {image_id} ({entry['doc_type']})", flush=True)
        start = time.time()
        
        extracted = process_image(
            image_id=image_id,
            image_file=entry["file"],
            images_root=images_root,
            doc_type=entry["doc_type"],
            fields=entry["fields"],
            use_cache=use_cache,
            model=model,
        )
        elapsed = time.time() - start
        if elapsed < 0.5:
            print(f"[{i}/{total}] \t-> CACHED {image_id}", flush=True)
        else:
            print(f"[{i}/{total}] FINISHED {image_id} in {elapsed:.1f}s", flush=True)
            
        predictions, debug = decide_predictions(extracted, threshold=threshold)
        
        with write_lock:
            all_predictions[image_id] = predictions
            all_debug[image_id] = debug
        _save_state()
        
        return image_id

    max_workers = 2
    print(f"Starting parallel processing with {max_workers} workers...")
    
    get_parser()
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_process_wrapper, i, entry): entry for i, entry in enumerate(images, 1)}
        for future in concurrent.futures.as_completed(futures):
            try:
                future.result()
            except Exception as exc:
                print(f"Image {futures[future]['id']} generated an exception: {exc}")

    print(f"\nWrote {len(all_predictions)} predictions to {out}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--images", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--threshold", type=float, default=0.5)
    ap.add_argument("--no-cache", action="store_true")
    ap.add_argument("--model", default="llama3.1")
    args = ap.parse_args()

    run(
        manifest_path=args.manifest,
        images_root=args.images,
        out_path=args.out,
        threshold=args.threshold,
        use_cache=not args.no_cache,
        model=args.model,
    )
