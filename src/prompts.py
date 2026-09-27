"""Builds the extraction prompt sent to the LLM for a given document."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from score import FIELD_TYPES  # noqa: E402

FIELD_DESCRIPTIONS = {
    "vendor_name": "The name of the company that issued the invoice.",
    "invoice_number": "The unique identifier for this invoice, often labeled 'Invoice No.', 'Invoice #', or similar in other languages.",
    "invoice_date": "The date the invoice was issued.",
    "due_date": "The date payment is due. Not every invoice has one.",
    "subtotal": "The amount before tax is added. Do NOT calculate it yourself; only extract it if explicitly listed as 'Subtotal' or similar. If not explicitly present, output null.",
    "tax_amount": "The tax amount added to the subtotal. If tax is split into CGST and SGST, you MUST add them together.",
    "total_amount": "The final amount owed.",
    "currency": "The ISO 4217 currency code (USD, EUR, GBP, INR, etc). Infer from symbols ($, Euro, £, Rupee) or explicit codes/text if not stated directly.",
    "merchant_name": "The name of the store/business that issued the receipt.",
    "transaction_date": "The date of the transaction/purchase.",
    "payment_method": "How payment was made. Must be one of: CASH, CARD, UPI, CHEQUE.",
    "employer_name": "The company/organization paying the employee.",
    "employee_name": "The person being paid.",
    "pay_period_start": "The start date of the pay period this stub covers.",
    "pay_period_end": "The end date of the pay period this stub covers.",
    "gross_pay": "Pay for THIS pay period only.",
    "net_pay": "Take-home pay for THIS pay period only.",
}

DOC_TYPE_LABEL = {
    "invoice": "an invoice",
    "receipt": "a retail/purchase receipt",
    "paystub": "a pay stub / payslip",
}

FORMAT_INSTRUCTIONS = {
    "text": "Plain text.",
    "date": "YYYY-MM-DD format.",
    "amount": "Plain number (e.g. 1840.00). No currency symbols/separators.",
    "code": "Uppercase ISO 4217 currency code (e.g. USD).",
    "enum": "Exactly one allowed value, uppercase.",
}

SYSTEM_INSTRUCTIONS = """You are an expert Data Extraction AI. 
Below is the text extracted via OCR from {doc_label}. The text has been formatted to roughly match its visual layout (left to right, top to bottom, separated by tabs).

OCR TEXT:
-------------------------
{ocr_text}
-------------------------

CRITICAL RULES:
{type_specific_rules}
- EXACT TEXT: When extracting text fields (names), extract the EXACT string including any trailing periods (.), commas, or special characters. Do NOT drop punctuation.
- DATES: Convert strictly to YYYY-MM-DD. CRITICAL: Pay attention to whether the format is DD/MM/YYYY or MM/DD/YYYY. If you see a number > 12 in the first position (e.g. 16/05), the format is strictly DD/MM/YYYY. If you see a number > 12 in the second position (e.g. 05/16), the format is strictly MM/DD/YYYY. Apply this format consistently to ALL dates on the page. NEVER guess.
- AMOUNTS: YOU ARE STRICTLY FORBIDDEN FROM CALCULATING ANY AMOUNTS! NEVER do math. ONLY extract numbers that are explicitly printed on the document. The label might be a synonym (e.g. "Amount Due" for total_amount, "VAT" for tax, etc.). If the value is not explicitly written on the page, output "null".
- ABSTAINING: YOU MUST ABSTAIN if a field is not physically printed on the page. Output "null" and confidence 0.0. NEVER invent dates like the 1st of the month. NEVER invent names. If you guess or calculate, you fail the task.

Extract the following fields from the text.
For each field, extract the value and provide a confidence score (0.0 to 1.0).
If a field is missing, output 'null' and confidence 0.0.

Format your response EXACTLY like this (two lines per field, nothing else):
{example_block}

Fields to extract:
{fields_block}"""

INVOICE_RULES = """- VENDOR NAME: This is the company ISSUING the invoice. NEVER extract the "Billed To", "Sold To", or customer name as the vendor!
- INVOICE NUMBER: Extract ONLY the invoice number. CRITICAL: Do NOT extract the Purchase Order (PO) Number! Strip prefixes like "Invoice No:", "Ref:".
- TAX: If tax is explicitly split into CGST and SGST, you MUST mathematically add them together to get the tax_amount."""

RECEIPT_RULES = """- MERCHANT NAME: This is the store/restaurant issuing the receipt (usually at the very top).
- PAYMENT METHOD: Must be exactly one of [CASH, CARD, UPI, CHEQUE]. If the payment method is not explicitly listed, output null! Do not guess!
- TRANSACTION DATE: Look for the date of purchase. Do NOT guess if missing."""

PAYSTUB_RULES = """- PAY PERIOD: Distinguish between the "Pay Date" (when the check was issued) and the "Pay Period" (the date range worked). If the start/end of the period is NOT explicitly listed, output null for pay_period_start and pay_period_end! Do NOT use the Pay Date as the period end.
- NAMES: Employer is the company paying. Employee is the person receiving. Do not swap them. If missing, output null. CRITICAL: Do NOT extract Bank names or Credit Unions as the Employer Name! If only a bank name is visible, output null for the employer.
- PAY AMOUNTS: Gross and Net Pay must be for the CURRENT period only. NEVER extract the YTD (Year-To-Date) totals."""

def build_extraction_prompt(doc_type: str, fields: list[str], ocr_text: str) -> str:
    doc_label = DOC_TYPE_LABEL.get(doc_type, doc_type)

    if doc_type == "invoice":
        type_specific_rules = INVOICE_RULES
    elif doc_type == "receipt":
        type_specific_rules = RECEIPT_RULES
    else:
        type_specific_rules = PAYSTUB_RULES

    field_lines = []
    for field in fields:
        ftype = FIELD_TYPES.get(field, "text")
        desc = FIELD_DESCRIPTIONS.get(field, "")
        fmt = FORMAT_INSTRUCTIONS.get(ftype, "")
        field_lines.append(f'- {field}: {desc} {fmt}')

    fields_block = "\n".join(field_lines)
    
    example_lines = []
    if len(fields) >= 2:
        example_lines = [
            f"{fields[0]}: extracted_value",
            "CONFIDENCE: 0.95",
            f"{fields[1]}: extracted_value",
            "CONFIDENCE: 0.80"
        ]
    else:
        example_lines = [
            f"{fields[0]}: extracted_value",
            "CONFIDENCE: 0.95"
        ]
    example_block = "\n".join(example_lines)

    return SYSTEM_INSTRUCTIONS.format(
        doc_label=doc_label,
        example_block=example_block,
        fields_block=fields_block,
        ocr_text=ocr_text,
        type_specific_rules=type_specific_rules
    )

