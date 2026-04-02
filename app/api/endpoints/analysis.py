import asyncio
import json
from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
import uuid
import logging

from app.schemas.analysis import AnalysisRequest, AnalysisResponse, ApprovalRequest
from app.schemas.status import ThreadStatusResponse
from app.services import agent_service
from app.services import document_service

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


@router.post("/start-with-pdf", response_model=AnalysisResponse, status_code=202)
async def start_analysis_with_pdf(
    background_tasks: BackgroundTasks,
    company_name: str = Form(...),
    file: UploadFile = File(...),
):
    """
    PDF yükleyerek yeni kredi risk analizi süreci başlatır.
    """
    normalized_company = (company_name or "").strip()
    if not normalized_company:
        raise HTTPException(status_code=400, detail="Şirket adı zorunludur.")

    try:
        file_bytes = await file.read()
        sha256 = document_service.validate_pdf_bytes(
            file_name=file.filename or "uploaded.pdf",
            content_type=file.content_type or "application/pdf",
            file_bytes=file_bytes,
        )

        existing_thread = agent_service.find_active_thread_for_company_and_sha256(
            company_name=normalized_company,
            document_sha256=sha256,
        )
        if existing_thread:
            logger.info(
                "Mevcut aktif thread tekrar kullanılıyor "
                f"company={normalized_company}, sha={sha256}, thread_id={existing_thread.thread_id}"
            )
            return AnalysisResponse(
                thread_id=existing_thread.thread_id,
                message=(
                    f"'{normalized_company}' için aynı PDF ile devam eden bir analiz bulundu. "
                    "Mevcut thread üzerinden devam ediliyor."
                ),
            )

        uploaded = document_service.upload_pdf_to_gcs(
            file_name=file.filename or "uploaded.pdf",
            content_type=file.content_type or "application/pdf",
            file_bytes=file_bytes,
            sha256=sha256,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"PDF upload sırasında hata company={normalized_company}: {e}")
        raise HTTPException(status_code=500, detail="PDF yüklenirken sunucu hatası oluştu.")
    finally:
        await file.close()

    thread_id = str(uuid.uuid4())
    request = AnalysisRequest(
        company_name=normalized_company,
        document_id=uploaded.document_id,
        document_object_key=uploaded.object_key,
        document_sha256=uploaded.sha256,
        document_original_name=uploaded.original_name,
        document_mime_type=uploaded.content_type,
        document_size_bytes=uploaded.size_bytes,
    )

    try:
        background_tasks.add_task(agent_service.start_analysis_task, thread_id, request)
    except Exception as e:
        logger.error(
            "Background task eklenemedi, orphan cleanup tetiklendi "
            f"thread_id={thread_id}, object_key={uploaded.object_key}: {e}"
        )
        try:
            document_service.delete_pdf_from_gcs(uploaded.object_key)
        except Exception as cleanup_error:
            logger.warning(
                "Orphan cleanup başarısız "
                f"thread_id={thread_id}, object_key={uploaded.object_key}: {cleanup_error}"
            )
        raise HTTPException(status_code=500, detail="Analiz kuyruğa alınamadı.")

    return AnalysisResponse(
        thread_id=thread_id,
        message=f"'{normalized_company}' için PDF tabanlı kredi analizi arka planda başlatıldı.",
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


@router.get("/recent")
async def get_recent_analyses(limit: int = 10):
    """
    Son analiz thread'lerini (status özeti ile) döner.
    UI tarafında hızlı devam listesi için kullanılır.
    """
    try:
        items = agent_service.list_recent_threads(limit=limit)
        return {
            "count": len(items),
            "items": items,
        }
    except Exception as e:
        logger.error(f"Recent analyses okunurken hata: {e}")
        raise HTTPException(status_code=500, detail="Son analizler okunurken sunucu hatası oluştu.")


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

                if payload.get("status") in ["completed", "failed", "canceled"]:
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
    
    if status.status == "canceled":
        return {"message": f"Thread ({thread_id}) kullanıcı tarafından iptal edilmiş durumda."}

    if not status.is_interrupted:
        logger.warning(f"Thread ({thread_id}) zaten işleniyor veya tamamlandı. Mevcut durum: {status.status}")
        return {"message": f"Thread ({thread_id}) zaten işleniyor. Mevcut durum: {status.status}"}
        
    background_tasks.add_task(agent_service.resume_analysis_task, thread_id, approval)
    
    action_text = "Onaylandı" if approval.is_approved else "Reddedildi"
    return {"message": f"Kredi analizi süreci '{action_text}' kararıyla arka planda devam ettiriliyor."}


@router.post("/{thread_id}/cancel", status_code=202)
async def cancel_analysis(thread_id: str):
    """
    Çalışan veya interrupt durumunda bekleyen analizi iptal eder.
    """
    try:
        agent_service.cancel_analysis_task(thread_id)
        return {"message": f"Thread ({thread_id}) iptal edildi."}
    except Exception as e:
        logger.error(f"Cancel sırasında hata thread_id={thread_id}: {e}")
        raise HTTPException(status_code=500, detail="İptal işlemi sırasında sunucu hatası oluştu.")
