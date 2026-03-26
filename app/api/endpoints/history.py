from fastapi import APIRouter, HTTPException
import logging

from fin_agent.agent import app as agent_app

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/{company_name}")
async def get_company_history(company_name: str):
    """
    Belirtilen şirket için LangGraph'ın Long-Term Memory (PostgresStore) içinde 
    neler hatırladığını (geçmiş kredi kararları, analiz gerekçeleri vb.) API üzerinden döner.
    """
    try:
        safe_company_name = company_name.replace(".", "").strip()
        
        if not hasattr(agent_app, "store") or agent_app.store is None:
             raise HTTPException(
                status_code=501, 
                detail="Sistemde (LangGraph app) kalıcı hafıza (Store) tanımlanmamış."
            )
             
        past_memory = agent_app.store.get(
            namespace=("companies", safe_company_name), 
            key="last_credit_decision"
        )
        
        if not past_memory:
            return {
                "company_name": company_name,
                "has_history": False,
                "message": "Bu şirket için daha önce yapılmış bir analiz bulunamadı. Yeni bir başvuru oluşturabilirsiniz."
            }
            
        return {
            "company_name": company_name,
            "has_history": True,
            "last_decision": past_memory.value.get("decision"),
            "reasoning": past_memory.value.get("reason"),
            "memory_timestamp": past_memory.updated_at.isoformat() if hasattr(past_memory, "updated_at") and past_memory.updated_at else None
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Geçmiş okunurken hata company={company_name}: {e}")
        raise HTTPException(status_code=500, detail="Hafıza sorgulanırken sunucu hatası oluştu.")