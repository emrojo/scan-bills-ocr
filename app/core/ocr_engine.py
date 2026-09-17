import json
import re
import time
import httpx
from typing import Dict, Any, Optional, List
from app.config import settings

class OCREngine:
    def __init__(self, base_url: Optional[str] = None):
        self.base_url = (base_url or settings.ollama_base_url).rstrip('/')
        
    async def is_ready(self) -> bool:
        """Checks if the Ollama service is up and responding."""
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                res = await client.get(f"{self.base_url}/api/tags")
                return res.status_code == 200
        except Exception:
            return False

    async def list_available_models(self) -> List[str]:
        """Returns the list of downloaded models in Ollama."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                res = await client.get(f"{self.base_url}/api/tags")
                if res.status_code == 200:
                    data = res.json()
                    return [m.get("name") for m in data.get("models", [])]
        except Exception:
            pass
        return []

    async def extract_from_image(
        self,
        image_base64: str,
        prompt: str,
        model: Optional[str] = None,
        force_json: bool = True
    ) -> Dict[str, Any]:
        """
        Sends the base64 image and prompt to the VLM (default: Qwen2.5-VL)
        and returns parsed structured output along with execution metrics.
        """
        target_model = model or settings.default_model
        start_time = time.time()
        
        payload = {
            "model": target_model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt,
                    "images": [image_base64]
                }
            ],
            "stream": False,
            "options": {
                "temperature": 0.1,  # Low temperature for deterministic factual extraction
                "num_predict": 2048
            }
        }
        
        if force_json:
            payload["format"] = "json"

        url = f"{self.base_url}/api/chat"
        
        try:
            async with httpx.AsyncClient(timeout=settings.timeout_seconds) as client:
                response = await client.post(url, json=payload)
                
            elapsed = round(time.time() - start_time, 2)
            
            if response.status_code != 200:
                return {
                    "success": False,
                    "error": f"Ollama error ({response.status_code}): {response.text}",
                    "raw_response": None,
                    "data": None,
                    "elapsed_seconds": elapsed,
                    "model_used": target_model
                }

            result_json = response.json()
            message_content = result_json.get("message", {}).get("content", "")
            parsed_data = self._clean_and_parse_json(message_content)
            
            return {
                "success": True,
                "data": parsed_data,
                "raw_response": message_content,
                "elapsed_seconds": elapsed,
                "model_used": target_model,
                "error": None if parsed_data is not None else "Response generated but could not be parsed into strict JSON"
            }
            
        except httpx.TimeoutException:
            elapsed = round(time.time() - start_time, 2)
            return {
                "success": False,
                "error": f"Request timed out after {settings.timeout_seconds}s",
                "raw_response": None,
                "data": None,
                "elapsed_seconds": elapsed,
                "model_used": target_model
            }
        except Exception as e:
            elapsed = round(time.time() - start_time, 2)
            return {
                "success": False,
                "error": f"Unexpected error: {str(e)}",
                "raw_response": None,
                "data": None,
                "elapsed_seconds": elapsed,
                "model_used": target_model
            }

    def _clean_and_parse_json(self, text: str) -> Optional[Dict[str, Any]]:
        """Cleans markdown wrappers and parses JSON objects."""
        if not text:
            return None
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
            cleaned = re.sub(r"\s*```$", "", cleaned)
            cleaned = cleaned.strip()
        try:
            return json.loads(cleaned)
        except Exception:
            match = re.search(r"(\{.*\})", cleaned, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(1))
                except Exception:
                    pass
            return None

ocr_engine = OCREngine()
