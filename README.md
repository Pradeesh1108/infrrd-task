# Document field extraction — take-home dataset

You get two sets of scanned-looking document images (invoices, receipts, pay
stubs): `dev/` with labels, `test/` without. Build a system that extracts the
requested fields per image, or abstains. Submit `predictions.json` for the
test set.

## Task

`manifest.json` lists, for every image, exactly which fields to extract. Some
fields on some images are genuinely unreadable or ambiguous; the correct
output for those is the string `ABSTAIN`. Every listed field must appear in
your predictions.

### Fields

| doc type | field | type |
|----------|-------|------|
| invoice | vendor_name | text |
| invoice | invoice_number | text |
| invoice | invoice_date, due_date | date |
| invoice | subtotal, tax_amount, total_amount | amount |
| invoice | currency | code |
| receipt | merchant_name | text |
| receipt | transaction_date | date |
| receipt | total_amount, tax_amount | amount |
| receipt | payment_method | enum: CASH, CARD, UPI, CHEQUE |
| receipt | currency | code |
| pay stub | employer_name, employee_name | text |
| pay stub | pay_period_start, pay_period_end | date |
| pay stub | gross_pay, net_pay | amount |
| pay stub | currency | code |

Notes: `total_amount` = subtotal + tax. Pay stub `gross_pay`/`net_pay` are
for the pay period, not year-to-date. `currency` is ISO 4217 (USD, EUR, GBP,
INR). Not every invoice has a due date; the manifest omits the field for
those images.

## Normalisation (applied to your predictions before comparison)

- date: `YYYY-MM-DD`; common formats like `March 14, 2026` or `03/14/2026`
  are normalised for you. Numeric dates on a document follow its locale:
  USD documents are month-first (`03/14/2026`), GBP, INR and EUR documents
  are day-first (`14/03/2026`, `14-03-2026`, `14.03.2026`). Output ISO.
- amount: two-decimal string, no separators or symbols (`1840.00`);
  `$1,840` is normalised for you. Documents use their locale's number
  format (`1,23,456.00` for INR, `1.234,56` or `1 234,56` for EUR in
  continental Europe); convert to `123456.00` / `1234.56` yourself.
- Documents are in English, German, French, Spanish or Dutch; some are
  handwritten, some are scanned sideways or upside down. Field names and
  label formats are the same regardless.
- A document may run to several pages; they are stacked top to bottom in
  one image, separated by a dark gutter. Totals may sit on the last page.
- text: whitespace trimmed/collapsed, compared case-insensitively;
  punctuation matters (`Harbor Supply Co.` ≠ `Harbor Supply`).
- enum/code: uppercased exact match.

## predictions.json

Same shape as `dev/labels.json`: image id → field → string value or
`"ABSTAIN"`.

```json
{
  "inv_01003": {
    "vendor_name": "Harbor Supply Co",
    "total_amount": "2005.60",
    "due_date": "ABSTAIN"
  }
}
```

## Scoring (per field)

| your prediction | ground truth | points |
|-----------------|--------------|--------|
| value | same value | +1.0 |
| value | different value | -2.0 |
| value | unanswerable field | -2.0 |
| ABSTAIN | unanswerable field | +1.0 |
| ABSTAIN | a value | -0.25 |
| missing | anything | -2.0 |

The score is the mean points per listed field. Wrong answers are punished
far harder than abstentions: abstain when you are not sure.

## Measure yourself on dev

```
python score.py --predictions my_predictions.json \
    --labels dev/labels.json --manifest dev/manifest.json
```

Reports `score`, `coverage` (fraction answered) and `precision_on_answered`.
Runs on the Python 3 standard library, no installs needed.
