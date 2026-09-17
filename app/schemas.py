from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field

class TaxDetail(BaseModel):
    tax_rate: Optional[float] = Field(None, description="Tax rate percentage (e.g. 21.0, 10.0, 4.0)")
    tax_base: Optional[float] = Field(None, description="Taxable amount subject to this rate")
    tax_amount: Optional[float] = Field(None, description="Calculated tax amount")

class InvoiceItem(BaseModel):
    description: str = Field(..., description="Description of the item, product, or service")
    quantity: Optional[float] = Field(None, description="Quantity")
    unit_price: Optional[float] = Field(None, description="Price per unit")
    total: Optional[float] = Field(None, description="Line total amount")
    tax_rate: Optional[float] = Field(None, description="Applied tax rate percentage")

class PartyInfo(BaseModel):
    name: Optional[str] = Field(None, description="Company or individual legal name")
    tax_id: Optional[str] = Field(None, description="Tax identification number (CIF, NIF, VAT ID, EIN)")
    address: Optional[str] = Field(None, description="Full street address")
    phone: Optional[str] = Field(None, description="Phone number")
    email: Optional[str] = Field(None, description="Email address")

class PIIBox(BaseModel):
    category: str = Field(..., description="Category of sensitive data (e.g. customer_name, customer_id, address, phone, iban)")
    text: Optional[str] = Field(None, description="The sensitive text content")
    box_2d: List[float] = Field(..., description="Bounding box [ymin, xmin, ymax, xmax] in 0-1000 normalized scale")

class InvoiceData(BaseModel):
    document_type: Optional[str] = Field("invoice", description="Document type: invoice, receipt, ticket, delivery_note")
    invoice_number: Optional[str] = Field(None, description="Invoice reference number or series")
    invoice_date: Optional[str] = Field(None, description="Issue date in YYYY-MM-DD format")
    due_date: Optional[str] = Field(None, description="Due date in YYYY-MM-DD format")
    currency: Optional[str] = Field("EUR", description="Currency code (e.g., EUR, USD, GBP)")
    
    issuer: PartyInfo = Field(default_factory=PartyInfo, description="Issuer / Seller details")
    receiver: PartyInfo = Field(default_factory=PartyInfo, description="Receiver / Customer details")
    
    taxable_base: Optional[float] = Field(None, description="Total subtotal / taxable base")
    total_tax: Optional[float] = Field(None, description="Total tax amount")
    total_amount: Optional[float] = Field(None, description="Grand total payable")
    
    taxes: List[TaxDetail] = Field(default_factory=list, description="Breakdown of taxes by rate")
    items: List[InvoiceItem] = Field(default_factory=list, description="Line item details")
    
    payment_method: Optional[str] = Field(None, description="Payment method (credit card, transfer, cash)")
    iban: Optional[str] = Field(None, description="Bank account IBAN if present")
    notes: Optional[str] = Field(None, description="Additional notes or remarks")
    pii_boxes: Optional[List[PIIBox]] = Field(None, description="Detected personal identifiable information bounding boxes")

class ExtractionResponse(BaseModel):
    success: bool
    data: Optional[Dict[str, Any]] = None
    raw_response: Optional[str] = None
    elapsed_seconds: float
    model_used: str
    page_count: int = 1
    redacted_image_base64: Optional[str] = None
    pii_boxes: Optional[List[Dict[str, Any]]] = None
    error: Optional[str] = None

class Base64ExtractionRequest(BaseModel):
    image_base64: str = Field(..., description="Base64-encoded image or PDF string")
    prompt: Optional[str] = Field(None, description="Custom prompt (Gemini-style). If omitted, default schema is used.")
    model: Optional[str] = Field(None, description="Target VLM model name (optional)")
    mime_type: Optional[str] = Field("image/jpeg", description="MIME type (e.g., image/jpeg, application/pdf)")
    redact_pii: Optional[bool] = Field(False, description="Whether to detect and redact personal data")
    redaction_style: Optional[str] = Field("blackout", description="Redaction visual style: 'blackout' or 'blur'")
