from pydantic import BaseModel, Field
from typing import Optional

class AnalysisRequest(BaseModel):
    company_name: str = Field(..., description="Analiz edilecek şirketin tam ticari unvanı", json_schema_extra={"examples": ["TÜRK HAVA YOLLARI A.O."]})
    document_id: Optional[str] = None
    document_object_key: Optional[str] = None
    document_sha256: Optional[str] = None
    document_original_name: Optional[str] = None
    document_mime_type: Optional[str] = None
    document_size_bytes: Optional[int] = None

class AnalysisResponse(BaseModel):
    thread_id: str = Field(..., description="Bu analiz süreci için oluşturulan benzersiz oturum kimliği")
    message: str = Field(..., description="Kullanıcıya gösterilecek durum mesajı")
    
class ApprovalRequest(BaseModel):
    is_approved: bool = Field(..., description="Risk denetçisinin (human-in-the-loop) karara onayı (True=Onay, False=Red)")
    note: Optional[str] = Field(default=None, description="Opsiyonel denetçi notu veya red/revizyon durumunda açıklama")