# app/extractor.py
import re
from fuzzywuzzy import fuzz
import math

AMOUNT_RE = re.compile(r'(?<!\d)(?:₹|\$|INR)?\s*([0-9]{1,3}(?:[,][0-9]{3})*(?:\.[0-9]{1,2})?|[0-9]+(?:\.[0-9]{1,2}))')

TOTAL_KEYWORDS = ['total', 'grand total', 'amount payable', 'net total', 'invoice total', 'amount due']
SUBTOTAL_KEYWORDS = ['subtotal', 'sub total', 'sub-total', 'sub-total:']

def parse_amount(s):
    m = AMOUNT_RE.search(s.replace(',', ''))
    if m:
        try:
            return float(m.group(1).replace(',', ''))
        except:
            return None
    return None

def iou(boxA, boxB):
    # boxes = (left, top, width, height)
    xA = max(boxA[0], boxB[0])
    yA = max(boxA[1], boxB[1])
    xB = min(boxA[0]+boxA[2], boxB[0]+boxB[2])
    yB = min(boxA[1]+boxA[3], boxB[1]+boxB[3])
    interW = max(0, xB - xA)
    interH = max(0, yB - yA)
    interArea = interW * interH
    boxAArea = boxA[2]*boxA[3]
    boxBArea = boxB[2]*boxB[3]
    if boxAArea + boxBArea - interArea == 0:
        return 0
    return interArea / float(boxAArea + boxBArea - interArea)

def dedupe_items(items, iou_thresh=0.4, text_thresh=90):
    kept = []
    for it in items:
        duplicate = False
        for k in kept:
            if abs(it['item_amount'] - k['item_amount']) < 0.01 and iou((it['left'], it['top'], it['width'], it['height']),
                                                                     (k['left'], k['top'], k['width'], k['height'])) > iou_thresh:
                duplicate = True
                break
            # fuzzy name similarity + similar amounts
            if fuzz.token_sort_ratio(it['item_name'], k['item_name']) > text_thresh and abs(it['item_amount'] - k['item_amount']) < 1.0:
                duplicate = True
                break
        if not duplicate:
            kept.append(it)
    return kept

def extract_line_items_from_lines(lines):
    # lines: list of {"text","left","top","width","height"}
    candidates = []
    for ln in lines:
        text = ln['text'].strip()
        amt = parse_amount(text)
        if amt is not None:
            # heuristic: split text by multiple spaces to find item name vs amount suffix
            # often amount at right; attempt to parse quantity and rate via additional regex
            # find potential quantity and rate
            qty = None
            rate = None
            # try find patterns like "2 x 50.00" or "2 50.00"
            m = re.search(r'([0-9]+)\s*[xX*]\s*([0-9]+\.[0-9]{1,2})', text)
            if m:
                qty = float(m.group(1))
                rate = float(m.group(2))
            # fallback: try "rate" near amount (not robust)
            name = text
            # remove amount token from name
            name = AMOUNT_RE.sub('', name).strip()
            candidates.append({
                "item_name": name if name else text,
                "item_amount": float(amt),
                "item_rate": rate,
                "item_quantity": qty,
                "left": ln['left'],
                "top": ln['top'],
                "width": ln['width'],
                "height": ln['height']
            })
    # dedupe
    deduped = dedupe_items(candidates)
    return deduped

def find_totals(lines):
    totals = {"detected_invoice_total": None, "detected_subtotals": []}
    for ln in lines:
        t = ln['text'].lower()
        for k in TOTAL_KEYWORDS:
            if k in t:
                amt = parse_amount(ln['text'])
                if amt:
                    totals['detected_invoice_total'] = float(amt)
        for k in SUBTOTAL_KEYWORDS:
            if k in t:
                amt = parse_amount(ln['text'])
                if amt:
                    totals['detected_subtotals'].append(float(amt))
    return totals
