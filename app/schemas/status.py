from pydantic import BaseModel, Field
from typing import List, Dict, Any, Literal, Optional

class AgentStateSchema(BaseModel):
    """LangGraph içindeki AgentState TypedDict yapısının Pydantic karşılığı."""
    company_name: str
    financial_kpis: List[Dict[str, Any]] = []
    market_sentiment: List[Dict[str, Any]] = []
    audit_log: List[str] = []
    loop_step: int = 0
    final_report: str = ""
    credit_decision: Literal["PENDING", "APPROVED", "REJECTED", "REVISION_REQUIRED", "CANCELED"] = "PENDING"
    next_node: str = "orchestrator"
    human_approval: Optional[bool] = None

class ThreadStatusResponse(BaseModel):
    """Mevcut analiz sürecinin (thread) durumunu UI'a dönmek için kullanılır."""
    thread_id: str = Field(..., description="Sorgulanan thread'in ID'si")
    status: Literal["running", "interrupted", "completed", "failed", "canceled"] = Field(..., description="Sürecin genel durumu")
    is_interrupted: bool = Field(..., description="Eğer sistem Human-in-the-Loop onayı bekliyorsa True olur")
    pending_node: Optional[str] = Field(default=None, description="Sıradaki veya aktif çalışan ajan (node) adı")
    activity_log: List[str] = Field(default_factory=list, description="Canlı ajan konsolu için işlem izleri")
    state: Optional[AgentStateSchema] = Field(default=None, description="Graph'ın güncel verisi/hafızası")
