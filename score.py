#!/usr/bin/env python3
"""Scorer for the document extraction take-home. Python standard library only.

Single submission:
  python score.py --predictions predictions.json --labels labels.json \
      --manifest manifest.json

Batch (one row per candidate, sorted by score):
  python score.py --batch submissions_dir --labels ... --manifest ... \
      --out leaderboard.csv

Per-field points:
  value    == label (after normalisation)  +1.0
  value    != label                        -2.0
  value    but label UNANSWERABLE          -2.0
  ABSTAIN  and label UNANSWERABLE          +1.0
  ABSTAIN  but label is a value            -0.25
  missing  (field not in predictions)      -2.0
"""
import argparse
import csv
import json
import re
import sys
from datetime import datetime
from pathlib import Path

UNANSWERABLE = "UNANSWERABLE"
ABSTAIN = "ABSTAIN"

FIELD_TYPES = {
    # invoice
    "vendor_name": "text", "invoice_number": "text", "invoice_date": "date",
    "due_date": "date", "subtotal": "amount", "tax_amount": "amount",
    "total_amount": "amount", "currency": "code",
    # receipt
    "merchant_name": "text", "transaction_date": "date",
    "payment_method": "enum",
    # pay stub
    "employer_name": "text", "employee_name": "text",
    "pay_period_start": "date", "pay_period_end": "date",
    "gross_pay": "amount", "net_pay": "amount",
}

_CURRENCY_JUNK = re.compile(r"[$€£₹,\s]|(?i:rs\.?)|(?i:\b(usd|eur|gbp|inr)\b)")
_DATE_FORMATS = (
    "%Y-%m-%d", "%Y/%m/%d", "%d %B %Y", "%B %d, %Y", "%b %d, %Y",
    "%d %b %Y", "%d-%b-%Y", "%m/%d/%Y", "%d.%m.%Y",
)


def normalize(value, ftype):
    value = str(value)
    if ftype == "amount":
        raw = _CURRENCY_JUNK.sub("", value.strip())
        try:
            return f"{float(raw):.2f}"
        except ValueError:
            return " ".join(value.split())
    if ftype == "date":
        t = " ".join(value.split())
        for fmt in _DATE_FORMATS:
            try:
                return datetime.strptime(t, fmt).strftime("%Y-%m-%d")
            except ValueError:
                continue
        return t
    if ftype in ("enum", "code"):
        return " ".join(value.split()).upper()
    return " ".join(value.split())


def values_match(pred, label, ftype):
    a, b = normalize(pred, ftype), normalize(label, ftype)
    if ftype == "text":
        return a.casefold() == b.casefold()
    return a == b


def score_submission(preds, labels, manifest, per_field=None):
    """Score one submission. per_field, if given, is called with
    (image_id, doc_type, field, pred, label, correct) for every listed field."""
    points = 0.0
    n_fields = answered = answered_correct = 0
    for entry in manifest["images"]:
        iid = entry["id"]
        img_labels = labels.get(iid)
        if img_labels is None:
            continue
        img_preds = preds.get(iid) or {}
        for field in entry["fields"]:
            label = img_labels[field]
            ftype = FIELD_TYPES[field]
            pred = img_preds.get(field)
            n_fields += 1
            if pred is None:
                points -= 2.0
                correct = False
            elif pred == ABSTAIN:
                points += 1.0 if label == UNANSWERABLE else -0.25
                correct = label == UNANSWERABLE
            else:
                answered += 1
                if label == UNANSWERABLE:
                    points -= 2.0
                    correct = False
                elif values_match(pred, label, ftype):
                    points += 1.0
                    correct = True
                    answered_correct += 1
                else:
                    points -= 2.0
                    correct = False
            if per_field is not None:
                per_field(iid, entry["doc_type"], field, pred, label, correct)
    out = {
        "score": round(points / n_fields, 4) if n_fields else 0.0,
        "coverage": round(answered / n_fields, 4) if n_fields else 0.0,
        "precision_on_answered": (round(answered_correct / answered, 4)
                                  if answered else 0.0),
        "fields": n_fields,
    }
    return out


def _load(path):
    with open(path) as f:
        return json.load(f)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--predictions")
    ap.add_argument("--batch")
    ap.add_argument("--labels", required=True)
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--out")
    ap.add_argument("--only-predicted", action="store_true",
                    help="score only the manifest images present in the "
                         "predictions file (partial/baseline runs)")
    args = ap.parse_args()
    if bool(args.predictions) == bool(args.batch):
        ap.error("pass exactly one of --predictions or --batch")

    labels = _load(args.labels)
    manifest = _load(args.manifest)

    if args.predictions:
        preds = _load(args.predictions)
        if args.only_predicted:
            manifest = dict(manifest, images=[i for i in manifest["images"]
                                              if i["id"] in preds])
        result = score_submission(preds, labels, manifest)
        print(json.dumps(result, indent=2))
        return

    rows = []
    for sub in sorted(Path(args.batch).iterdir()):
        pf = sub / "predictions.json"
        if not sub.is_dir() or not pf.is_file():
            continue
        try:
            r = score_submission(_load(pf), labels, manifest)
        except Exception as exc:  # a malformed submission scores as unusable
            r = {"score": "", "coverage": "", "precision_on_answered": "",
                 "fields": "", "error": str(exc)[:80]}
        rows.append({"candidate_id": sub.name, **r})
    rows.sort(key=lambda r: (isinstance(r["score"], float), r["score"]),
              reverse=True)
    fieldnames = ["candidate_id", "score", "coverage",
                  "precision_on_answered", "fields"]
    if any("error" in r for r in rows):
        fieldnames.append("error")
    out = args.out or "leaderboard.csv"
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {out} ({len(rows)} candidates)")


if __name__ == "__main__":
    sys.exit(main())
