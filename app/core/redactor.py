import io
import base64
from typing import List, Dict, Any, Tuple
from PIL import Image, ImageDraw, ImageFilter
import pymupdf as fitz

def normalize_box(box_2d: List[Any], width: int, height: int, padding: int = 4) -> Tuple[int, int, int, int]:
    """
    Converts normalized coordinates [ymin, xmin, ymax, xmax] (0-1000 scale)
    into absolute pixel coordinates (x0, y0, x1, y1) with safety padding.
    """
    if len(box_2d) < 4:
        return (0, 0, 0, 0)
        
    ymin, xmin, ymax, xmax = [float(v) for v in box_2d[:4]]
    
    # Scale from 0-1000 to pixel dimensions
    x0 = int((xmin / 1000.0) * width) - padding
    y0 = int((ymin / 1000.0) * height) - padding
    x1 = int((xmax / 1000.0) * width) + padding
    y1 = int((ymax / 1000.0) * height) + padding
    
    # Clamp to image boundaries
    x0 = max(0, min(width - 1, x0))
    y0 = max(0, min(height - 1, y0))
    x1 = max(0, min(width, x1))
    y1 = max(0, min(height, y1))
    
    return (x0, y0, x1, y1)

def apply_image_redaction(
    image: Image.Image,
    boxes: List[Dict[str, Any]],
    style: str = "blackout",
    blur_radius: int = 16
) -> Image.Image:
    """
    Applies redaction onto an image using provided bounding boxes.
    Supported styles:
      - 'blackout': Solid privacy black rectangle.
      - 'blur': Gaussian blur filter on the sensitive area.
    """
    result = image.copy().convert("RGB")
    width, height = result.size
    draw = ImageDraw.Draw(result)
    
    for item in boxes:
        box_coords = item.get("box_2d") or item.get("box") or item.get("coordinates")
        if not box_coords or not isinstance(box_coords, list):
            continue
            
        x0, y0, x1, y1 = normalize_box(box_coords, width, height)
        if x1 <= x0 or y1 <= y0:
            continue
            
        if style == "blur":
            # Crop region, apply heavy blur, and paste back
            box_width = x1 - x0
            box_height = y1 - y0
            if box_width > 1 and box_height > 1:
                cropped = result.crop((x0, y0, x1, y1))
                # Apply blur scaled to region size
                radius = max(6, min(blur_radius, int(min(box_width, box_height) / 2)))
                blurred = cropped.filter(ImageFilter.GaussianBlur(radius=radius))
                result.paste(blurred, (x0, y0))
                # Draw subtle border around blurred area
                draw.rectangle([x0, y0, x1, y1], outline=(120, 120, 120), width=1)
        else:
            # Default: Solid black rectangle
            draw.rectangle([x0, y0, x1, y1], fill=(0, 0, 0))
            
    return result

def apply_pdf_redaction(
    pdf_bytes: bytes,
    page_boxes_list: List[List[Dict[str, Any]]],
    style: str = "blackout"
) -> bytes:
    """
    Performs true physical redaction on a PDF document using PyMuPDF.
    Removes the underlying text stream permanently so text cannot be copied.
    """
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    
    for page_num in range(len(doc)):
        if page_num >= len(page_boxes_list):
            break
            
        page = doc[page_num]
        p_rect = page.rect
        p_width, p_height = p_rect.width, p_rect.height
        boxes = page_boxes_list[page_num]
        
        for item in boxes:
            box_coords = item.get("box_2d") or item.get("box")
            if not box_coords or not isinstance(box_coords, list):
                continue
                
            x0, y0, x1, y1 = normalize_box(box_coords, int(p_width), int(p_height))
            if x1 <= x0 or y1 <= y0:
                continue
                
            rect = fitz.Rect(x0, y0, x1, y1)
            # PyMuPDF native true redaction annotation
            fill_color = (0, 0, 0) if style != "blur" else (0.4, 0.4, 0.4)
            page.add_redact_annot(rect, fill=fill_color)
            
        page.apply_redactions()
        
    output_bytes = doc.tobytes(deflate=True, garbage=3)
    doc.close()
    return output_bytes

def image_to_base64(image: Image.Image, format: str = "JPEG", quality: int = 92) -> str:
    """Converts PIL Image to base64 string."""
    buffer = io.BytesIO()
    image.save(buffer, format=format, quality=quality, optimize=True)
    return base64.b64encode(buffer.getvalue()).decode("utf-8")
