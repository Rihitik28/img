# Bill Extraction & Reconciliation API

This repository contains a baseline pipeline and API to extract line items from invoices/bills and reconcile totals.
It provides `POST /extract-bill-data` that accepts a JSON body with a `document` URL and returns extracted line items and reconciliation information.

## Features (baseline)
- Download PDF/image from URL
- Convert PDFs to images
- Preprocess images for OCR (deskew, binarize)
- OCR using Tesseract + line bounding box grouping
- Heuristic extraction of items (name, quantity, rate, amount)
- Deduplication to avoid double-counting
- Detect subtotal / invoice total lines and reconcile
- FastAPI endpoint that returns required schema

## Installation

### Requirements
- Python 3.9+
- Tesseract binary installed:
  - Ubuntu: `sudo apt-get install -y tesseract-ocr`
  - macOS: `brew install tesseract`

### Install Python packages
fastapi
uvicorn[standard]
pillow
pytesseract
pdf2image
opencv-python-headless
python-multipart
numpy
pandas
regex
python-Levenshtein
fuzzywuzzy
requests
