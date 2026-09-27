from src.normalize import normalize_field

ABSTAIN = "ABSTAIN"
_AMOUNT_TRIANGLE = {"subtotal", "tax_amount", "total_amount"}

def _amounts_consistent(subtotal, tax_amount, total_amount, tolerance=0.01) -> bool | None:
    try:
        s, t, tot = float(subtotal), float(tax_amount), float(total_amount)
    except (TypeError, ValueError):
        return None
    return abs((s + t) - tot) <= tolerance

def score_field_confidence(field: str, raw_value, normalized_value, model_confidence: float, arithmetic_ok: bool | None) -> float:
    if raw_value is None: return 0.0
    if normalized_value is None: return 0.1
    score = 0.5 + (0.3 * model_confidence)
    if field in _AMOUNT_TRIANGLE:
        if arithmetic_ok is True: score += 0.2
        elif arithmetic_ok is False: score -= 0.4
    return max(0.0, min(1.0, score))

def decide_predictions(extracted: dict, threshold: float = 0.76) -> tuple[dict, dict]:
    currency_hint = None
    if "currency" in extracted and extracted["currency"]["value"]:
        currency_hint = str(extracted["currency"]["value"]).strip().upper()

    normalized = {}
    for field, entry in extracted.items():
        raw_value = entry.get("value")
        normalized[field] = normalize_field(field, raw_value, currency_hint=currency_hint)

    arithmetic_ok = None
    if _AMOUNT_TRIANGLE.issubset(extracted.keys()):
        arithmetic_ok = _amounts_consistent(
            normalized.get("subtotal"), normalized.get("tax_amount"), normalized.get("total_amount")
        )

    predictions = {}
    debug_info = {}

    for field, entry in extracted.items():
        raw_value = entry.get("value")
        model_confidence = entry.get("confidence", 0.0)
        norm_value = normalized[field]

        conf_score = score_field_confidence(
            field, raw_value, norm_value, model_confidence,
            arithmetic_ok if field in _AMOUNT_TRIANGLE else None,
        )

        if conf_score >= threshold and norm_value is not None:
            val_lower = norm_value.lower()
            
            # HEURISTIC 1: Reject Bank names for employers
            if field == "employer_name" and ("bank" in val_lower or "credit union" in val_lower or "fcu" in val_lower):
                predictions[field] = ABSTAIN
            # HEURISTIC 2: Reject obviously fake merchant names
            elif field == "merchant_name" and any(x in val_lower for x in [
                "thank you", "drive safe", "regpos", "reglane", "billed in",
                "straat", "nagar", "lane", "mainroad"
            ]):
                predictions[field] = ABSTAIN
            # HEURISTIC 3: net_pay shouldn't be larger than gross_pay if both are present
            elif field == "net_pay" and "gross_pay" in normalized and normalized["gross_pay"]:
                try:
                    if float(norm_value) > float(normalized["gross_pay"]):
                        predictions[field] = ABSTAIN
                    else:
                        predictions[field] = norm_value
                except:
                    predictions[field] = norm_value
            # HEURISTIC 4: Restrict payment methods
            elif field == "payment_method" and norm_value.upper() not in ["CASH", "CARD", "UPI", "CHEQUE"]:
                predictions[field] = ABSTAIN
            # HEURISTIC 5: Tax cannot be exactly 0.00
            elif field == "tax_amount":
                try:
                    if float(norm_value) == 0.0:
                        predictions[field] = ABSTAIN
                    else:
                        predictions[field] = norm_value
                except:
                    predictions[field] = norm_value
            # HEURISTIC 6: Invoice number cannot start with REF, PO, SO
            elif field == "invoice_number" and (norm_value.upper().startswith("REF-") or norm_value.upper().startswith("PO-") or norm_value.upper().startswith("P0-") or norm_value.upper().startswith("SO-")):
                predictions[field] = ABSTAIN
            # HEURISTIC 8: Tax Amount strict check
            elif field == "tax_amount":
                # If we couldn't verify arithmetic, be extremely skeptical of tax
                if arithmetic_ok is not True:
                    if "total_amount" in normalized and normalized["total_amount"]:
                        try:
                            t_val = float(norm_value)
                            tot_val = float(normalized["total_amount"])
                            # Tax is usually < 20% of total. If it's more, or exactly 0 without proof, abstain.
                            if t_val > 0.22 * tot_val or t_val == 0.0:
                                predictions[field] = ABSTAIN
                            else:
                                predictions[field] = norm_value
                        except:
                            predictions[field] = norm_value
                    else:
                        # No total amount and no arithmetic = abstain
                        predictions[field] = ABSTAIN
                else:
                    predictions[field] = norm_value
            # HEURISTIC 9: Pay period end dates are often hallucinated if start is missing
            elif field == "pay_period_end":
                if "pay_period_start" not in normalized or not normalized["pay_period_start"]:
                    predictions[field] = ABSTAIN
                else:
                    predictions[field] = norm_value
            # HEURISTIC 10: Vendor / Employer name length constraints
            elif field in ["vendor_name", "employer_name", "merchant_name"]:
                if len(norm_value) < 3 or len(norm_value) > 40:
                    predictions[field] = ABSTAIN
                else:
                    predictions[field] = norm_value
            # HEURISTIC 11: Dates
            elif field in ["invoice_date", "due_date", "transaction_date", "pay_period_start", "pay_period_end"]:
                if len(norm_value) != 10 or not (1990 <= int(norm_value[:4]) <= 2030):
                    predictions[field] = ABSTAIN
                else:
                    predictions[field] = norm_value
            else:
                predictions[field] = norm_value
        else:
            predictions[field] = ABSTAIN

        debug_info[field] = {
            "raw_value": raw_value,
            "normalized_value": norm_value,
            "confidence_score": round(conf_score, 3),
            "decision": predictions[field],
        }

    # HEURISTIC 7: Date Order
    if "pay_period_start" in predictions and "pay_period_end" in predictions:
        s = predictions["pay_period_start"]
        e = predictions["pay_period_end"]
        if s != ABSTAIN and e != ABSTAIN and s > e:
            predictions["pay_period_start"] = ABSTAIN
            predictions["pay_period_end"] = ABSTAIN
            debug_info["pay_period_start"]["decision"] = ABSTAIN
            debug_info["pay_period_end"]["decision"] = ABSTAIN

    return predictions, debug_info
