# app/main.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import requests
from io import BytesIO
from app.ocr_utils import pdf_bytes_to_images, preprocess_pil_image, ocr_image_with_boxes
from app.extractor import extract_line_items_from_lines, find_totals
import math, time

app = FastAPI()

class RequestBody(BaseModel):
    document: str

@app.post("/extract-bill-data")
async def extract_bill_data(payload: RequestBody):
    start = time.time()
    url = payload.document
    # 1. fetch
    try:
        r = requests.get(url, timeout=20)
        r.raise_for_status()
        content = r.content
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not fetch document: {e}")

    # 2. determine file type: simple check for pdf
    images = []
    if content[:4] == b'%PDF':
        images = pdf_bytes_to_images(content, dpi=300)
    else:
        # attempt to open as image
        from PIL import Image
        im = Image.open(BytesIO(content)).convert('RGB')
        images = [im]

    pagewise_line_items = []
    total_items = 0
    all_detected_amount = 0.0
    invoice_totals = []
    for i, pil_img in enumerate(images):
        prep = preprocess_pil_image(pil_img)
        lines = ocr_image_with_boxes(prep)
        items = extract_line_items_from_lines(lines)
        totals = find_totals(lines)
        if totals['detected_invoice_total']:
            invoice_totals.append(totals['detected_invoice_total'])
        # Clean output to required schema
        bill_items = []
        for it in items:
            bill_items.append({
                "item_name": it['item_name'],
                "item_amount": round(float(it['item_amount']),2),
                "item_rate": round(float(it['item_rate']),2) if it['item_rate'] else None,
                "item_quantity": round(float(it['item_quantity']),2) if it['item_quantity'] else None
            })
            all_detected_amount += it['item_amount']
        pagewise_line_items.append({
            "page_no": str(i+1),
            "page_type": "Bill Detail",
            "bill_items": bill_items
        })
        total_items += len(bill_items)

    # dedupe across pages is already performed per-page; optionally dedupe cross-page (skipped here)
    # final total: sum of unique item amounts (our items already deduped per-page)
    final_total = round(all_detected_amount,2)
    # Choose most-likely invoice total if detected (take last non-null)
    actual_invoice_total = invoice_totals[-1] if invoice_totals else None

    token_usage = {"total_tokens": 0, "input_tokens": 0, "output_tokens": 0}
    elapsed = time.time() - start

    response = {
        "is_success": True,
        "token_usage": token_usage,
        "data": {
            "pagewise_line_items": pagewise_line_items,
            "total_item_count": total_items,
            "final_total_extracted": final_total,
            "detected_invoice_total": actual_invoice_total,
            "reconciliation": {
                "difference": round((actual_invoice_total - final_total) if actual_invoice_total else None,2) if actual_invoice_total else None,
                "status": ("MATCH" if actual_invoice_total and abs(actual_invoice_total - final_total) < 0.01 else "MISMATCH" if actual_invoice_total else "UNKNOWN")
            },
            "processing_time_seconds": round(elapsed,2)
        }
    }
    return response
