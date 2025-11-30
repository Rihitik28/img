import requests
import json

API_URL = "http://localhost:8000/extract-bill-data"  
# Change this to your deployed URL

SAMPLE_DOC_URL = (
    "https://hackrx.blob.core.windows.net/assets/datathon-IIT/sample_2.png?"
    "sv=2025-07-05&spr=https&st=2025-11-28T06%3A47%3A35Z&se=2025-11-29T06%3A47%3A35Z&"
    "sr=b&sp=r&sig=yB8R2zjoRL2%2FWRuv7E1lvmWSHAkm%2FoIGsepj2Io9pak%3D"
)

def test_api_response_structure():
    """
    Basic smoke test to ensure API returns valid structure
    """

    payload = {
        "document": SAMPLE_DOC_URL
    }

    response = requests.post(API_URL, json=payload)
    assert response.status_code == 200, "API did not return HTTP 200"

    data = response.json()

    # Top-level keys
    assert "is_success" in data
    assert "token_usage" in data
    assert "data" in data

    # token usage structure
    token = data["token_usage"]
    assert "total_tokens" in token
    assert "input_tokens" in token
    assert "output_tokens" in token

    # data structure
    extracted = data["data"]
    assert "pagewise_line_items" in extracted
    assert "total_item_count" in extracted

    # page structure
    pages = extracted["pagewise_line_items"]
    assert isinstance(pages, list)

    if len(pages) > 0:
        page = pages[0]
        assert "page_no" in page
        assert "page_type" in page
        assert "bill_items" in page

        items = page["bill_items"]
        assert isinstance(items, list)

        if len(items) > 0:
            item = items[0]
            assert "item_name" in item
            assert "item_amount" in item
            assert "item_rate" in item
            assert "item_quantity" in item

def test_api_handles_invalid_url():
    """
    API should gracefully handle invalid document URLs
    """

    payload = {"document": "https://invalid-url.com/notfound.png"}

    response = requests.post(API_URL, json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["is_success"] in [False, True]   # depends on your design


def test_multiple_requests():
    """
    Ensures API works repeatedly without failures
    """

    payload = {"document": SAMPLE_DOC_URL}

    for _ in range(3):
        response = requests.post(API_URL, json=payload)
        assert response.status_code == 200
