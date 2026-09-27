#!/bin/bash
set -e

echo "Running inference on DEV set..."
uv run --python 3.11 python3 -m src.run_pipeline --manifest dev/manifest.json --images dev/images --out dev_predictions.json

echo "Scoring DEV set predictions..."
uv run --python 3.11 python3 score.py --predictions dev_predictions.json --labels dev/labels.json --manifest dev/manifest.json > outputs/score2.json
echo "Dev score successfully saved to outputs/score2.json!"

echo "Running inference on TEST set..."
uv run --python 3.11 python3 -m src.run_pipeline --manifest test/manifest.json --images test/images --out predictions.json

echo "Done!"