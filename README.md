# ⚡ ScanBills OCR: Autonomous Semantic Document Extraction & PII Redaction Engine

> **Zero-Cost, Privacy-First, Local Vision-Language OCR & Redaction Service.**  
> Drop-in replacement for the **Google Gemini Multimodal API** (`gemini-1.5-flash` / `gemini-2.0-flash`) and GPT-4o for invoices, receipts, and bills, powered by **Qwen2.5-VL** with **Automated Personally Identifiable Information (PII) Censorship**.

---

## 🌟 Why ScanBills OCR?

- **100% Free & Unlimited**: Zero API subscriptions, no rate limits, no recurring costs.
- **Gemini-Level Accuracy**: Powered by **Qwen2.5-VL**, the open-weights leader in visual document understanding, complex table parsing, and multi-language invoice extraction.
- **🛡️ Built-in PII Redaction / Anonymization**: Automatically locates and physically blacks out or blurs sensitive personal data (customer names, DNI/NIE, addresses, phones, emails, IBANs, signatures).
- **Physical PDF Sanitization**: When redacting PDFs, PyMuPDF physically strips the underlying text stream—the text cannot be copied or highlighted.
- **🔒 Hardened Network Security**:
  - **Ollama is 100% private**: No open ports exposed to the host or internet.
  - **Localhost-only API**: Web service binds strictly to `127.0.0.1:8000`, blocking direct external access.
  - **Shared `proxy-network`**: Automatically connects to an existing `proxy-network` or creates it if not present.
- **Works on Any Hardware**: Runs on **NVIDIA GPUs**, **CPU-only servers/VPS**, or **AMD Radeon GPUs**.
- **Autonomous "Deploy & Forget"**: Docker Compose stacks with persistent model volumes and self-healing startup.

---

## 🔒 Network Architecture & Security

```
Internet / External Traffic
           │
           ▼
┌─────────────────────────┐
│ External Nginx Proxy    │ (Host daemon OR Docker container)
└──────────┬──────────────┘
           │
           ▼ (Only via 127.0.0.1:8000 OR via proxy-network)
┌─────────────────────────────────────────────────────────────┐
│ Docker Network: proxy-network (shared / auto-created)       │
│                                                             │
│  ┌──────────────────────┐        ┌───────────────────────┐  │
│  │ scanbills-web        │        │ scanbills-ollama      │  │
│  │ Ports:               │───────▶│ (NO host ports)       │  │
│  │ 127.0.0.1:8000:8000  │        │ Internal: 11434       │  │
│  └──────────────────────┘        └───────────────────────┘  │
│                                                             │
│  ┌──────────────────────┐                                   │
│  │ scanbills-model-     │                                   │
│  │ puller (init)        │                                   │
│  └──────────────────────┘                                   │
└─────────────────────────────────────────────────────────────┘
  ❌ External access to 11434 is BLOCKED
  ❌ Direct external access to 8000 is BLOCKED (only 127.0.0.1)
```

---

## 🌐 External Nginx Reverse Proxy Configuration

Place this configuration in your external Nginx to expose ScanBills securely (with SSL/TLS, domain names, or authentication):

### Option A: Nginx running on the Host OS (`/etc/nginx/sites-available/ocr.conf`)
```nginx
server {
    listen 80;
    server_name ocr.yourdomain.com;

    # Increase max upload size for multi-page PDFs / high-res scans
    client_max_body_size 60M;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Generous timeout for large document inference
        proxy_read_timeout 300s;
        proxy_connect_timeout 300s;
        proxy_send_timeout 300s;
    }
}
```

### Option B: Nginx running as a Docker container on `proxy-network`
```nginx
location / {
    proxy_pass http://scanbills-web:8000;
    client_max_body_size 60M;
    proxy_read_timeout 300s;
}
```

---

## 🖥️ Hardware Compatibility Matrix

| Environment | Compose File | Recommended Model | RAM / VRAM Needed | Latency / Doc |
| :--- | :--- | :--- | :--- | :--- |
| **NVIDIA GPU** (RTX 3060/4060/5060, A10G, T4) | `docker-compose.yml` | **`qwen2.5vl:7b`** | 6–8 GB VRAM | ~2–6 sec |
| **CPU-Only VPS** (Hetzner, AWS, Linode, DigitalOcean) | `docker-compose.cpu.yml` | **`qwen2.5vl:3b`** | 3–4 GB RAM | ~5–12 sec |
| **AMD GPU** (Radeon RX 6000/7000, Instinct ROCm) | `docker-compose.rocm.yml` | **`qwen2.5vl:7b`** | 6–8 GB VRAM | ~3–7 sec |

---

## 🚀 Autonomous Server Deployment

### 1. NVIDIA GPU Server Deployment (Default)

```bash
git clone https://github.com/your-username/scan-bills.git
cd scan-bills
docker compose up -d
```

### 2. CPU-Only Server Deployment (No GPU Required)

```bash
docker compose -f docker-compose.cpu.yml up -d
```

### 3. AMD Radeon GPU Deployment (ROCm)

```bash
docker compose -f docker-compose.rocm.yml up -d
```

---

## 🛡️ Automatic PII Redaction & Document Sanitization

### What Gets Redacted?
- **Personal Names**: Individual customers or recipients (preserves public corporate business names).
- **National Tax IDs**: DNI, NIE, Passports, SSNs.
- **Contact Details**: Personal phone numbers and email addresses.
- **Residential Addresses**: Street addresses of private individuals.
- **Banking & Card Data**: Bank account IBANs and payment card numbers.
- **Handwritten Signatures**: Manual signatures and personal stamps.

### Visual Styles Available:
- **`blackout`** (Default): High-contrast solid black privacy tape. Recommended for regulatory (GDPR / HIPAA) compliance.
- **`blur`**: High-radius Gaussian blur filter over the sensitive coordinates.

---

## 🔌 API Integration Guide

### 1. Extract JSON + Redact PII in a Single Call

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/extract" \
  -F "file=@invoice.pdf" \
  -F "redact_pii=true" \
  -F "redaction_style=blackout"
```

### 2. Directly Download the Redacted File (`/api/v1/redact`)

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/redact" \
  -F "file=@customer_receipt.jpg" \
  -F "style=blackout" \
  --output sanitized_receipt.jpg
```

---

## 📄 License
MIT License. Free for personal, commercial, and enterprise deployment.
