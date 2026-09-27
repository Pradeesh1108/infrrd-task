"""Preprocessing steps applied before extraction: primarily rotation
correction. Detection asks the VLM itself (cheap, short-response call)
rather than building a custom heuristic — more robust across handwriting,
faxes, and varied layouts than text-line/Hough-transform approaches.
"""
import io
from pathlib import Path

from PIL import Image

from src.ollama_client import call_vlm_with_retry

_ROTATION_PROMPT = (
    "Look at this document image. Ignoring its current orientation, "
    "what rotation (clockwise, in degrees) would make the text upright "
    "and readable in normal reading order? "
    "Answer with exactly one number: 0, 90, 180, or 270. "
    "No other text."
)


def detect_rotation(image_path: str, model: str = "qwen3-vl:8b") -> int:
    """Returns the clockwise rotation (0/90/180/270) needed to make the
    document upright. Defaults to 0 (no rotation) if the model's answer
    can't be parsed — safer than guessing a wrong rotation."""
    try:
        response = call_vlm_with_retry(image_path, _ROTATION_PROMPT, model=model, timeout=300, max_retries=5)
    except Exception:
        return 0

    text = response.strip()
    for angle in (0, 90, 180, 270):
        if str(angle) in text:
            return angle
    return 0


def correct_rotation(image_path: str, angle: int, out_path: str) -> str:
    """Rotates the image by `angle` degrees clockwise and saves it to
    out_path. Returns out_path. If angle is 0, just copies the original
    (still writes out_path, so callers always have a consistent file to
    point extraction at)."""
    img = Image.open(image_path)
    if angle != 0:
        # PIL's rotate() is counter-clockwise, so negate for clockwise input
        img = img.rotate(-angle, expand=True)
    img.save(out_path)
    return out_path


def preprocess_image(
    image_path: str,
    cache_dir: str,
    image_id: str,
    model: str = "qwen3-vl:8b",
    enable_rotation: bool = True,
) -> tuple[str, int]:
    """Full preprocessing for one image: detect + correct rotation.
    Returns (path_to_use_for_extraction, detected_angle).

    Corrected images are cached under cache_dir/preprocessed/ so re-runs
    don't re-call the model for rotation detection either.
    """
    if not enable_rotation:
        return image_path, 0

    cache_path = Path(cache_dir) / "preprocessed" / f"{image_id}.png"
    if cache_path.exists():
        # we don't cache the angle itself here for simplicity — if you need
        # it for debug/analysis, re-run detect_rotation directly (it's cheap)
        return str(cache_path), -1  # -1 = "was cached, angle unknown"

    angle = detect_rotation(image_path, model=model)
    cache_path.parent.mkdir(parents=True, exist_ok=True)

    if angle == 0:
        # no rotation needed — just copy so downstream always reads from cache_path
        Image.open(image_path).save(cache_path)
    else:
        correct_rotation(image_path, angle, str(cache_path))

    return str(cache_path), angle


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        print("Usage: python -m src.preprocess <path_to_image>")
        sys.exit(1)

    test_image = sys.argv[1]
    angle = detect_rotation(test_image)
    print(f"Detected rotation: {angle} degrees clockwise")

    out_path = "/tmp/rotation_test.png"
    correct_rotation(test_image, angle, out_path)
    print(f"Corrected image saved to {out_path}")