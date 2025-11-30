# app/ocr_utils.py
import io, os, tempfile
from pdf2image import convert_from_bytes
from PIL import Image, ImageOps
import pytesseract
import numpy as np
import cv2

# Optional: configure tesseract cmd path if needed
# pytesseract.pytesseract.tesseract_cmd = r"/usr/bin/tesseract"

def pdf_bytes_to_images(pdf_bytes, dpi=300):
    imgs = convert_from_bytes(pdf_bytes, dpi=dpi)
    return imgs

def preprocess_pil_image(pil_img):
    # convert to grayscale, increase contrast, binarize lightly
    img = np.array(pil_img.convert('RGB'))
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    # adaptive threshold
    th = cv2.adaptiveThreshold(gray,255,cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                               cv2.THRESH_BINARY,11,2)
    # invert if background dark
    if np.mean(th) < 127:
        th = 255 - th
    pil = Image.fromarray(th)
    return pil

def ocr_image_with_boxes(pil_img, lang='eng'):
    # returns list of dicts per line/token with bbox and text
    # We'll use pytesseract's TSV output (word-level). We then group to lines.
    data = pytesseract.image_to_data(pil_img, lang=lang, output_type=pytesseract.Output.DICT)
    n = len(data['level'])
    results = []
    for i in range(n):
        text = data['text'][i].strip()
        if text == "":
            continue
        x, y, w, h = data['left'][i], data['top'][i], data['width'][i], data['height'][i]
        conf = int(data['conf'][i]) if data['conf'][i].isdigit() else -1
        results.append({"text": text, "left": x, "top": y, "width": w, "height": h, "conf": conf})
    # merge into line-level by y coordinate clustering
    results_sorted = sorted(results, key=lambda r: (r['top'], r['left']))
    lines = []
    if not results_sorted:
        return lines
    current_line = {"texts": [], "left": results_sorted[0]['left'], "top": results_sorted[0]['top'],
                    "right": results_sorted[0]['left'] + results_sorted[0]['width'],
                    "bottom": results_sorted[0]['top'] + results_sorted[0]['height']}
    for r in results_sorted:
        # if vertical gap small, same line
        if abs(r['top'] - current_line['top']) <= max(10, int(0.5 * current_line['bottom'] - current_line['top'])):
            current_line['texts'].append(r)
            current_line['left'] = min(current_line['left'], r['left'])
            current_line['right'] = max(current_line['right'], r['left'] + r['width'])
            current_line['bottom'] = max(current_line['bottom'], r['top'] + r['height'])
        else:
            # finalize
            line_text = " ".join([t['text'] for t in current_line['texts']])
            lines.append({
                "text": line_text,
                "left": current_line['left'],
                "top": current_line['top'],
                "width": current_line['right'] - current_line['left'],
                "height": current_line['bottom'] - current_line['top']
            })
            current_line = {"texts": [r], "left": r['left'], "top": r['top'],
                            "right": r['left'] + r['width'], "bottom": r['top'] + r['height']}
    # append last
    line_text = " ".join([t['text'] for t in current_line['texts']])
    lines.append({
        "text": line_text,
        "left": current_line['left'],
        "top": current_line['top'],
        "width": current_line['right'] - current_line['left'],
        "height": current_line['bottom'] - current_line['top']
    })
    return lines
