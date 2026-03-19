from typing import Annotated, List, Dict, Any, Literal, TypedDict
from langchain_core.messages import BaseMessage
import operator

class AgentState(TypedDict):
    company_name: str
    
    instructions: Annotated[List[BaseMessage], operator.add]

    messages: Annotated[List[BaseMessage], operator.add]
    
    # Finansal Veriler
    financial_kpis: Annotated[List[Dict[str, Any]], operator.add]
    
    # Piyasa Analizi
    market_sentiment: Annotated[List[Dict[str, Any]], operator.add]
    
    # Reflection: Auditor'ın düzeltme talepleri buraya yazılır
    audit_log: Annotated[List[str], operator.add]

    # Analiz sürecinin hangi aşamada olduğunu (step) takip eden bir sayaç (Max loops engellemek için)
    loop_step: Annotated[int, operator.add]
    
    # Karar ve Raporlama
    final_report: str
    
    # Kredi kararı için tipler
    credit_decision: Literal["PENDING", "APPROVED", "REJECTED", "REVISION_REQUIRED"]
    
    next_node: str
