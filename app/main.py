import os
import io
import time
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Response
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image

from app.config import settings
from app.schemas import ExtractionResponse, Base64ExtractionRequest
from app.core.ocr_engine import ocr_engine
from app.core.preprocessor import process_uploaded_bytes
from app.core.prompts import build_prompt, SYSTEM_REDACTION_ONLY_PROMPT
from app.core.redactor import (
    apply_image_redaction,
    apply_pdf_redaction,
    image_to_base64
)

app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description="Autonomous, cost-free local OCR and semantic document extraction service with automatic PII redaction, powered by Qwen2.5-VL."
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

def _get_index_response():
    index_file = os.path.join(static_dir, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file, media_type="text/html; charset=utf-8")
    return JSONResponse(
        status_code=404,
        content={"error": "index.html not found in static folder."}
    )

@app.get("/", include_in_schema=False)
async def serve_root():
    return _get_index_response()

@app.get("/app", include_in_schema=False)
async def serve_app_alias():
    return _get_index_response()

@app.get("/index.html", include_in_schema=False)
async def serve_index_alias():
    return _get_index_response()

@app.get("/api/v1/health", tags=["System"])
async def health_check():
    """Checks the status of the Ollama inference engine and available models."""
    ready = await ocr_engine.is_ready()
    models = await ocr_engine.list_available_models() if ready else []
    return {
        "status": "healthy" if ready else "ollama_not_responding",
        "ollama_connected": ready,
        "available_models": models,
        "default_model": settings.default_model,
        "app_version": settings.version
    }

@app.get("/api/v1/models", tags=["System"])
async def list_models():
    """Lists all vision models available in the local backend."""
    models = await ocr_engine.list_available_models()
    return {"models": models, "default": settings.default_model}

@app.post("/api/v1/extract", response_model=ExtractionResponse, tags=["OCR & Redaction"])
async def extract_from_file(
    file: UploadFile = File(..., description="Document image (.jpg, .png, .webp) or PDF file"),
    prompt: Optional[str] = Form(None, description="Optional custom prompt (Gemini-style)."),
    model: Optional[str] = Form(None, description="VLM model name (e.g. qwen2.5vl:7b, qwen2.5vl:3b)"),
    force_json: bool = Form(True, description="Enforce strict JSON output format"),
    redact_pii: bool = Form(False, description="Detect and censor personal data (names, IDs, IBANs, etc.)"),
    redaction_style: str = Form("blackout", description="Redaction visual style: 'blackout' or 'blur'")
):
    """
    Upload an invoice, receipt image, or PDF document and extract structured JSON data.
    Optionally redacts PII and returns the modified sanitized image.
    """
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
        
    filename = file.filename or "doc.png"
    is_pdf = filename.lower().endswith(".pdf") or content.startswith(b"%PDF")

    try:
        images_b64 = process_uploaded_bytes(content, filename)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error processing document: {str(e)}")

    effective_prompt = build_prompt(prompt, include_pii_boxes=redact_pii)
    target_model = model or settings.default_model
    
    # Single-page document (most common)
    if len(images_b64) == 1:
        result = await ocr_engine.extract_from_image(
            image_base64=images_b64[0],
            prompt=effective_prompt,
            model=target_model,
            force_json=force_json
        )
        result["page_count"] = 1

        # Apply PII redaction if requested
        if redact_pii and result.get("success"):
            data_dict = result.get("data") or {}
            pii_boxes = data_dict.get("pii_boxes") or []
            result["pii_boxes"] = pii_boxes

            if pii_boxes:
                try:
                    if is_pdf:
                        redacted_pdf = apply_pdf_redaction(content, [pii_boxes], style=redaction_style)
                        redacted_imgs = process_uploaded_bytes(redacted_pdf, "redacted.pdf")
                        result["redacted_image_base64"] = redacted_imgs[0] if redacted_imgs else None
                    else:
                        orig_img = Image.open(io.BytesIO(content))
                        redacted_img = apply_image_redaction(orig_img, pii_boxes, style=redaction_style)
                        result["redacted_image_base64"] = image_to_base64(redacted_img)
                except Exception as red_err:
                    result["error"] = f"Extraction succeeded, but redaction failed: {str(red_err)}"

        return JSONResponse(status_code=200 if result["success"] else 500, content=result)
    
    # Multi-page PDF document
    start_time = time.time()
    pages_results = []
    all_pii_boxes = []

    for idx, img_b64 in enumerate(images_b64):
        p_res = await ocr_engine.extract_from_image(
            image_base64=img_b64,
            prompt=f"[Page {idx+1} of {len(images_b64)}]\n{effective_prompt}",
            model=target_model,
            force_json=force_json
        )
        p_data = p_res.get("data") or {}
        pages_results.append(p_data or p_res.get("raw_response"))
        if redact_pii:
            all_pii_boxes.append(p_data.get("pii_boxes") or [])
        
    total_elapsed = round(time.time() - start_time, 2)
    
    redacted_b64 = None
    if redact_pii:
        try:
            redacted_pdf = apply_pdf_redaction(content, all_pii_boxes, style=redaction_style)
            redacted_imgs = process_uploaded_bytes(redacted_pdf, "redacted.pdf")
            redacted_b64 = redacted_imgs[0] if redacted_imgs else None
        except Exception:
            pass

    return {
        "success": True,
        "data": {"pages": pages_results},
        "raw_response": None,
        "elapsed_seconds": total_elapsed,
        "model_used": target_model,
        "page_count": len(images_b64),
        "redacted_image_base64": redacted_b64,
        "error": None
    }

@app.post("/api/v1/redact", tags=["OCR & Redaction"])
async def redact_document_file(
    file: UploadFile = File(..., description="Image or PDF to censor personal data from"),
    style: str = Form("blackout", description="Redaction visual style: 'blackout' or 'blur'"),
    model: Optional[str] = Form(None, description="Target VLM model name")
):
    """
    Directly returns the censored/anonymized file (image/jpeg or application/pdf).
    """
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    filename = file.filename or "document.png"
    is_pdf = filename.lower().endswith(".pdf") or content.startswith(b"%PDF")
    target_model = model or settings.default_model

    try:
        images_b64 = process_uploaded_bytes(content, filename)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error processing file: {str(e)}")

    if is_pdf:
        page_boxes_list = []
        for img_b64 in images_b64:
            res = await ocr_engine.extract_from_image(
                image_base64=img_b64,
                prompt=SYSTEM_REDACTION_ONLY_PROMPT,
                model=target_model,
                force_json=True
            )
            data = res.get("data") or {}
            page_boxes_list.append(data.get("pii_boxes") or [])

        redacted_pdf_bytes = apply_pdf_redaction(content, page_boxes_list, style=style)
        return Response(
            content=redacted_pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'inline; filename="redacted_{filename}"'}
        )
    else:
        res = await ocr_engine.extract_from_image(
            image_base64=images_b64[0],
            prompt=SYSTEM_REDACTION_ONLY_PROMPT,
            model=target_model,
            force_json=True
        )
        data = res.get("data") or {}
        boxes = data.get("pii_boxes") or []

        orig_img = Image.open(io.BytesIO(content))
        redacted_img = apply_image_redaction(orig_img, boxes, style=style)

        out_buffer = io.BytesIO()
        redacted_img.save(out_buffer, format="JPEG", quality=92)
        out_bytes = out_buffer.getvalue()

        return Response(
            content=out_bytes,
            media_type="image/jpeg",
            headers={"Content-Disposition": f'inline; filename="redacted_{filename}.jpg"'}
        )

@app.post("/api/v1/extract/base64", response_model=ExtractionResponse, tags=["OCR & Redaction"])
async def extract_from_base64(req: Base64ExtractionRequest):
    """
    Direct extraction from a base64-encoded image string.
    """
    effective_prompt = build_prompt(req.prompt, include_pii_boxes=bool(req.redact_pii))
    target_model = req.model or settings.default_model
    result = await ocr_engine.extract_from_image(
        image_base64=req.image_base64,
        prompt=effective_prompt,
        model=target_model,
        force_json=True
    )
    result["page_count"] = 1
    return JSONResponse(status_code=200 if result["success"] else 500, content=result)
