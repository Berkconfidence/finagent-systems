from pydantic import BaseModel, Field
from typing import Optional

class AnalysisRequest(BaseModel):
    company_name: str = Field(..., description="Analiz edilecek şirketin tam ticari unvanı", json_schema_extra={"examples": ["TÜRK HAVA YOLLARI A.O."]})
    # İleride PDF/Base64 eklenecek.

class AnalysisResponse(BaseModel):
    thread_id: str = Field(..., description="Bu analiz süreci için oluşturulan benzersiz oturum kimliği")
    message: str = Field(..., description="Kullanıcıya gösterilecek durum mesajı")
    
class ApprovalRequest(BaseModel):
    is_approved: bool = Field(..., description="Risk denetçisinin (human-in-the-loop) karara onayı (True=Onay, False=Red)")
    note: Optional[str] = Field(default=None, description="Opsiyonel denetçi notu veya red/revizyon durumunda açıklama")