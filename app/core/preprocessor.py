import io
import base64
from typing import List
from PIL import Image, ImageOps
import pymupdf as fitz
from app.config import settings

def process_uploaded_bytes(data: bytes, filename: str) -> List[str]:
    lower_name = filename.lower()
    if lower_name.endswith('.pdf') or data.startswith(b'%PDF'):
        return _process_pdf(data)
    else:
        return [_process_image(data)]

def _process_pdf(pdf_bytes: bytes) -> List[str]:
    images_base64 = []
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    zoom = settings.pdf_dpi / 72.0
    matrix = fitz.Matrix(zoom, zoom)
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        pix = page.get_pixmap(matrix=matrix, alpha=False)
        img_bytes = pix.tobytes("jpeg")
        b64 = _process_image(img_bytes)
        images_base64.append(b64)
    doc.close()
    return images_base64

def _process_image(image_bytes: bytes) -> str:
    img = Image.open(io.BytesIO(image_bytes))
    try:
        img = ImageOps.exif_transpose(img)
    except Exception:
        pass
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")
    max_dim = settings.max_image_dimension
    width, height = img.size
    if max(width, height) > max_dim:
        scale = max_dim / float(max(width, height))
        new_w = int(width * scale)
        new_h = int(height * scale)
        img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
    output_buffer = io.BytesIO()
    img.save(output_buffer, format="JPEG", quality=92, optimize=True)
    return base64.b64encode(output_buffer.getvalue()).decode("utf-8")

