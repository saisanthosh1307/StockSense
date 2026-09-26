import io
import json
import base64
import qrcode
from typing import Dict, Any

def generate_qr_code_base64(data: Dict[str, Any]) -> str:
    """
    Encodes JSON payload into a QR Code PNG and returns a Base64 data URI string.
    """
    json_str = json.dumps(data, default=str)
    
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=8,
        border=3,
    )
    qr.add_data(json_str)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    
    b64_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{b64_str}"

def parse_qr_payload(raw_string: str) -> Dict[str, Any]:
    try:
        return json.loads(raw_string)
    except Exception:
        # Fallback for plain text barcode/SKU
        return {"type": "RAW_TEXT", "value": raw_string}
