from fastapi import APIRouter, BackgroundTasks, HTTPException
import uuid
import logging

from app.schemas.analysis import AnalysisRequest, AnalysisResponse, ApprovalRequest
from app.schemas.status import ThreadStatusResponse
from app.services import agent_service

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/start", response_model=AnalysisResponse, status_code=202)
async def start_analysis(request: AnalysisRequest, background_tasks: BackgroundTasks):
    """
    Yeni bir kredi risk analizi süreci başlatır.
    İşlem uzun sürebileceği için süreç arka planda yürütülür.
    Hemen bir thread_id dönülür, böylece istemci (UI) süreci polling ile takip edebilir.
    """
    thread_id = str(uuid.uuid4())
    
    background_tasks.add_task(agent_service.start_analysis_task, thread_id, request)
    
    return AnalysisResponse(
        thread_id=thread_id,
        message=f"'{request.company_name}' için kredi analizi arka planda başlatıldı."
    )

@router.get("/{thread_id}/status", response_model=ThreadStatusResponse)
async def get_analysis_status(thread_id: str):
    """
    Belirtilen thread_id için DB'den güncel durumu, çıkan sonuçları ve interrupt bekleyip beklemediğini sorgular.
    """
    try:
        status = agent_service.get_thread_status(thread_id)
        return status
    except Exception as e:
        logger.error(f"Status okunurken hata thread_id={thread_id}: {e}")
        raise HTTPException(status_code=500, detail="Durum sorgulanırken sunucu hatası oluştu.")

@router.post("/{thread_id}/approve", status_code=202)
async def approve_analysis(thread_id: str, approval: ApprovalRequest, background_tasks: BackgroundTasks):
    """
    İnsan onayı (Human-in-the-Loop) bekleyen (interrupted state) bir süreci uyandırır ve karar yönünde devam ettirir.
    """
    status = agent_service.get_thread_status(thread_id)
    
    if not status.is_interrupted:
        raise HTTPException(
            status_code=400, 
            detail=f"Thread ({thread_id}) şu anda insan onayı beklemiyor. Mevcut durum: {status.status}"
        )
        
    background_tasks.add_task(agent_service.resume_analysis_task, thread_id, approval)
    
    action_text = "Onaylandı" if approval.is_approved else "Reddedildi"
    return {"message": f"Kredi analizi süreci '{action_text}' kararıyla arka planda devam ettiriliyor."}
