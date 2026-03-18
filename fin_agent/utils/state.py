from typing import Annotated, List, TypedDict, Dict, Any
import operator
from langchain_core.messages import BaseMessage

class AgentState(TypedDict):
    # Ana rapor konusu/şirket adı
    company_name: str
    
    # Mesaj geçmişi (Persistence/Memory için kritik)
    # Annotated + operator.add sayesinde ajan mesajları birbirini silmez, eklenir.
    messages: Annotated[List[BaseMessage], operator.add]
    
    # Paralel çalışan işçilerden (Workers) gelecek sonuçlar
    # Orchestrator-Worker desenindeki 'completed_sections' mantığı
    analysis_results: Annotated[List[Dict[str, Any]], operator.add]
    
    # Nihai risk raporu ve onay durumu
    final_report: str
    is_approved: bool  # Risk Auditor onayı


# fin_agent/utils/state.py
from typing import Annotated, TypedDict
import operator

class SimpleState(TypedDict):
    # 'operator.add' sayesinde mesajlar silinmez, liste olarak birikir.
    messages: Annotated[list, operator.add]
    user_name: str