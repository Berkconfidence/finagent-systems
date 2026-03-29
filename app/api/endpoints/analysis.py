import asyncio
import json
from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import StreamingResponse
import uuid
import logging

from app.schemas.analysis import AnalysisRequest, AnalysisResponse, ApprovalRequest
from app.schemas.status import ThreadStatusResponse
from app.services import agent_service

logger = logging.getLogger(__name__)

router = APIRouter()


def _format_sse(event_name: str, data: dict) -> str:
    return f"event: {event_name}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"

@router.post("/start", response_model=AnalysisResponse, status_code=202)
async def start_analysis(request: AnalysisRequest, background_tasks: BackgroundTasks):
    """
    Yeni bir kredi risk analizi süreci başlatır.
    İşlem uzun sürebileceği için süreç arka planda yürütülür.
    Hemen bir thread_id dönülür, böylece istemci (UI) süreci polling ile takip edebilir.
    """
    existing_thread = agent_service.find_active_thread_for_company(request.company_name)
    if existing_thread:
        logger.info(
            f"Mevcut aktif thread tekrar kullanılıyor company={request.company_name}, thread_id={existing_thread.thread_id}"
        )
        return AnalysisResponse(
            thread_id=existing_thread.thread_id,
            message=(
                f"'{request.company_name}' için devam eden bir analiz bulundu. "
                "Mevcut thread üzerinden devam ediliyor."
            ),
        )

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


@router.get("/{thread_id}/events")
async def stream_analysis_events(thread_id: str):
    """
    Thread durumunu SSE (Server-Sent Events) ile canlı olarak yayınlar.
    İstemci tarafında EventSource ile dinlenebilir.
    """

    async def event_generator():
        last_fingerprint = None
        heartbeat_tick = 0

        while True:
            try:
                status = agent_service.get_thread_status(thread_id)
                payload = status.model_dump()
                fingerprint = json.dumps(payload, sort_keys=True, ensure_ascii=False)

                if fingerprint != last_fingerprint:
                    event_name = "snapshot" if last_fingerprint is None else "status_update"
                    last_fingerprint = fingerprint
                    heartbeat_tick = 0
                    yield _format_sse(event_name, payload)
                else:
                    heartbeat_tick += 1
                    if heartbeat_tick >= 5:
                        heartbeat_tick = 0
                        yield _format_sse("heartbeat", {"thread_id": thread_id})

                if payload.get("status") in ["completed", "failed"]:
                    yield _format_sse("end", payload)
                    break

                await asyncio.sleep(1)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"SSE stream hatası thread_id={thread_id}: {e}")
                yield _format_sse("error", {"thread_id": thread_id, "detail": str(e)})
                break

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )

@router.post("/{thread_id}/approve", status_code=202)
async def approve_analysis(thread_id: str, approval: ApprovalRequest, background_tasks: BackgroundTasks):
    """
    İnsan onayı (Human-in-the-Loop) bekleyen (interrupted state) bir süreci uyandırır ve karar yönünde devam ettirir.
    """
    status = agent_service.get_thread_status(thread_id)
    
    if not status.is_interrupted:
        logger.warning(f"Thread ({thread_id}) zaten işleniyor veya tamamlandı. Mevcut durum: {status.status}")
        return {"message": f"Thread ({thread_id}) zaten işleniyor. Mevcut durum: {status.status}"}
        
    background_tasks.add_task(agent_service.resume_analysis_task, thread_id, approval)
    
    action_text = "Onaylandı" if approval.is_approved else "Reddedildi"
    return {"message": f"Kredi analizi süreci '{action_text}' kararıyla arka planda devam ettiriliyor."}
