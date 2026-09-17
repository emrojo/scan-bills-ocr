# -*- coding: utf-8 -*-
import asyncio
import io
import base64
import time
import json
from PIL import Image, ImageDraw
from app.core.ocr_engine import ocr_engine
from app.core.prompts import build_prompt

def create_sample_invoice() -> str:
    img = Image.new('RGB', (800, 1000), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    
    # Encabezado Emisor
    draw.rectangle([(30, 30), (770, 120)], fill=(240, 245, 250))
    draw.text((50, 45), "SOLUCIONES TECNOLOGICAS DEL NORTE S.L.", fill=(20, 30, 60))
    draw.text((50, 70), "CIF: B-98765432  |  Calle Gran Via 45, 3B, 28013 Madrid", fill=(60, 60, 60))
    draw.text((50, 90), "Email: facturacion@solucionesnorte.es  |  Tel: 912 345 678", fill=(80, 80, 80))
    
    # Datos Factura
    draw.text((50, 150), "FACTURA NUM: INV-2026-089", fill=(0, 0, 0))
    draw.text((50, 175), "FECHA DE EMISION: 2026-09-12", fill=(0, 0, 0))
    draw.text((50, 200), "VENCIMIENTO: 2026-10-12", fill=(0, 0, 0))
    
    # Datos Cliente
    draw.rectangle([(420, 140), (770, 230)], outline=(200, 200, 200), width=1)
    draw.text((435, 150), "CLIENTE:", fill=(100, 100, 100))
    draw.text((435, 170), "Innovacion Digital S.A.", fill=(0, 0, 0))
    draw.text((435, 190), "NIF: A-12345678", fill=(0, 0, 0))
    draw.text((435, 210), "Avda. Diagonal 600, Barcelona", fill=(80, 80, 80))
    
    # Tabla de conceptos
    draw.rectangle([(40, 260), (760, 290)], fill=(30, 40, 60))
    draw.text((50, 268), "DESCRIPCION", fill=(255, 255, 255))
    draw.text((460, 268), "CANT.", fill=(255, 255, 255))
    draw.text((550, 268), "PRECIO", fill=(255, 255, 255))
    draw.text((680, 268), "TOTAL", fill=(255, 255, 255))
    
    # LÃ­nea 1
    draw.text((50, 310), "Consultoria de Arquitectura Cloud (Horas)", fill=(20, 20, 20))
    draw.text((475, 310), "10", fill=(20, 20, 20))
    draw.text((560, 310), "80.00 EUR", fill=(20, 20, 20))
    draw.text((685, 310), "800.00 EUR", fill=(20, 20, 20))
    draw.line([(40, 340), (760, 340)], fill=(220, 220, 220), width=1)
    
    # LÃ­nea 2
    draw.text((50, 355), "Soporte Tecnico Mensual Dedicado", fill=(20, 20, 20))
    draw.text((475, 355), "1", fill=(20, 20, 20))
    draw.text((550, 355), "250.00 EUR", fill=(20, 20, 20))
    draw.text((685, 355), "250.00 EUR", fill=(20, 20, 20))
    draw.line([(40, 385), (760, 385)], fill=(220, 220, 220), width=1)
    
    # Totales
    draw.text((500, 420), "BASE IMPONIBLE:", fill=(40, 40, 40))
    draw.text((680, 420), "1050.00 EUR", fill=(40, 40, 40))
    
    draw.text((500, 450), "IVA (21%):", fill=(40, 40, 40))
    draw.text((680, 450), "220.50 EUR", fill=(40, 40, 40))
    
    draw.rectangle([(480, 480), (760, 520)], fill=(230, 240, 255))
    draw.text((500, 492), "TOTAL A PAGAR:", fill=(0, 0, 80))
    draw.text((670, 492), "1270.50 EUR", fill=(0, 0, 80))
    
    # Pie
    draw.text((50, 560), "Forma de pago: Transferencia bancaria", fill=(60, 60, 60))
    draw.text((50, 580), "IBAN: ES91 2100 0418 4502 0005 1332", fill=(60, 60, 60))
    
    img.save("test_invoice.jpg", format="JPEG", quality=95)
    
    buffered = io.BytesIO()
    img.save(buffered, format="JPEG", quality=95)
    return base64.b64encode(buffered.getvalue()).decode("utf-8")

async def main():
    print("[*] Generando factura de prueba...")
    b64_img = create_sample_invoice()
    print("[OK] Factura guardada como test_invoice.jpg")
    
    print("[*] Verificando motor Ollama...")
    ready = await ocr_engine.is_ready()
    if not ready:
        print("[ERROR] Ollama no responde en http://127.0.0.1:11434")
        return
        
    models = await ocr_engine.list_available_models()
    print(f"[OK] Modelos detectados en Ollama: {models}")
    
    prompt = build_prompt()
    print("[*] Enviando imagen y prompt a Qwen2.5-VL en la RTX 5060 Ti...")
    start = time.time()
    result = await ocr_engine.extract_from_image(
        image_base64=b64_img,
        prompt=prompt,
        model="qwen2.5vl:7b",
        force_json=True
    )
    total_time = round(time.time() - start, 2)
    
    print(f"\n[RESULTADO] (Tiempo API: {result.get('elapsed_seconds')}s, Total: {total_time}s)")
    print("=" * 60)
    if result.get("data"):
        print(json.dumps(result["data"], indent=2, ensure_ascii=False))
    else:
        print("Raw response:", result.get("raw_response"))
        print("Error:", result.get("error"))
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
