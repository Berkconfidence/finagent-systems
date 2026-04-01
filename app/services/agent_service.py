from langgraph.types import Command
import logging
import threading
from datetime import datetime
from fin_agent.agent import app as agent_app, pool
from app.schemas.analysis import AnalysisRequest, ApprovalRequest
from app.schemas.status import ThreadStatusResponse, AgentStateSchema

logger = logging.getLogger(__name__)
_canceled_threads: set[str] = set()
_cancel_lock = threading.Lock()
_thread_activity_logs: dict[str, list[str]] = {}
_activity_lock = threading.Lock()


def _is_canceled(thread_id: str) -> bool:
    with _cancel_lock:
        return thread_id in _canceled_threads


def _mark_canceled(thread_id: str):
    with _cancel_lock:
        _canceled_threads.add(thread_id)


def _push_activity(thread_id: str, message: str):
    timestamp = datetime.now().strftime("%H:%M:%S")
    line = f"[{timestamp}] {message}"
    with _activity_lock:
        items = _thread_activity_logs.setdefault(thread_id, [])
        items.append(line)
        if len(items) > 200:
            _thread_activity_logs[thread_id] = items[-200:]


def _get_activity(thread_id: str) -> list[str]:
    with _activity_lock:
        return list(_thread_activity_logs.get(thread_id, []))


def cancel_analysis_task(thread_id: str):
    """
    Thread iptal işaretini set eder ve mümkünse state'i CANCELED olarak yazar.
    """
    _mark_canceled(thread_id)
    _push_activity(thread_id, "Kullanıcı analizi iptal etti.")
    config = {"configurable": {"thread_id": thread_id}}
    try:
        agent_app.update_state(
            config,
            {
                "credit_decision": "CANCELED",
                "final_report": "Analiz kullanıcı tarafından iptal edildi.",
                "next_node": "END",
            },
        )
    except Exception as e:
        logger.warning(f"[{thread_id}] İptal state güncellemesi atlandı: {e}")


def _normalize_company_name(value: str) -> str:
    return (value or "").replace(".", "").strip().upper()


def find_active_thread_for_company(company_name: str, limit: int = 200) -> ThreadStatusResponse | None:
    """
    Checkpoint tablosundan şirket için en güncel thread'leri tarar,
    halen running/interrupted olan ilk thread'i döner.
    """
    target = _normalize_company_name(company_name)
    if not target:
        return None

    try:
        query = """
        WITH latest AS (
            SELECT DISTINCT ON (thread_id)
                thread_id,
                checkpoint_id,
                checkpoint
            FROM checkpoints
            ORDER BY thread_id, checkpoint_id DESC
        )
        SELECT
            thread_id,
            checkpoint_id,
            COALESCE(checkpoint->'channel_values'->>'company_name', '') AS company_name
        FROM latest
        ORDER BY checkpoint_id DESC
        LIMIT %s
        """

        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (limit,))
                rows = cur.fetchall()

        for thread_id, _checkpoint_id, row_company_name in rows:
            if _normalize_company_name(row_company_name) != target:
                continue

            thread_status = get_thread_status(thread_id)
            if thread_status.status in ["running", "interrupted"]:
                return thread_status

    except Exception as e:
        logger.error(f"Aktif thread aranırken hata company={company_name}: {e}")

    return None


def list_recent_threads(limit: int = 10):
    """
    Son checkpoint'lerden thread bazlı özet liste döner.
    UI'da son işlemler / hızlı devam et listesi için kullanılabilir.
    """
    safe_limit = max(1, min(limit, 50))

    query = """
    WITH latest AS (
        SELECT DISTINCT ON (thread_id)
            thread_id,
            checkpoint_id,
            checkpoint
        FROM checkpoints
        ORDER BY thread_id, checkpoint_id DESC
    )
    SELECT
        thread_id,
        checkpoint_id,
        COALESCE(checkpoint->'channel_values'->>'company_name', '') AS company_name
    FROM latest
    ORDER BY checkpoint_id DESC
    LIMIT %s
    """

    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (safe_limit,))
            rows = cur.fetchall()

    items = []
    for thread_id, checkpoint_id, company_name in rows:
        try:
            status = get_thread_status(thread_id)
            items.append(
                {
                    "thread_id": thread_id,
                    "company_name": company_name,
                    "status": status.status,
                    "is_interrupted": status.is_interrupted,
                    "pending_node": status.pending_node,
                    "last_checkpoint_id": checkpoint_id,
                }
            )
        except Exception as e:
            logger.error(f"Recent thread status okunamadı thread_id={thread_id}: {e}")

    return items

def start_analysis_task(thread_id: str, request_data: AnalysisRequest):
    """
    Arka planda LangGraph analiz sürecini başlatır.
    FastAPI BackgroundTasks tarafından çağrılacaktır.
    """
    logger.info(f"[{thread_id}] Yeni analiz başlıyor: {request_data.company_name}")
    _push_activity(thread_id, f"Analiz başlatıldı: {request_data.company_name}")
    
    initial_state = {
        "company_name": request_data.company_name,
        "instructions": [],
        "messages": [],
        "financial_kpis": [],
        "market_sentiment": [],
        "audit_log": [],
        "loop_step": 0,
        "final_report": "",
        "credit_decision": "PENDING",
        "next_node": "orchestrator",
        "human_approval": None
    }
    
    config = {"configurable": {"thread_id": thread_id}}
    
    try:
        for step in agent_app.stream(initial_state, config=config):
            if _is_canceled(thread_id):
                logger.warning(f"[{thread_id}] Süreç iptal edildi, stream durduruluyor.")
                cancel_analysis_task(thread_id)
                break

            if "__interrupt__" in step:
                logger.warning(f"[{thread_id}] SÜREÇ İNSAN ONAYI İÇİN DURAKLATILDI (Interrupt)")
                _push_activity(thread_id, "HITL onayı bekleniyor (interrupt).")
                break
                
            for node_name, updates in step.items():
                logger.info(f"[{thread_id}] >>> Ajan Tamamlandı: {node_name}")
                _push_activity(thread_id, f"Node tamamlandı: {node_name}")
                
        logger.info(f"[{thread_id}] Analiz süreci durdu (Bitti veya Kesintiye Uğradı).")
        if not _is_canceled(thread_id):
            _push_activity(thread_id, "Analiz akışı durdu (tamamlandı veya beklemede).")
        
    except Exception as e:
        logger.error(f"[{thread_id}] Analiz sırasında hata: {str(e)}")
        _push_activity(thread_id, f"Hata: {str(e)}")

def resume_analysis_task(thread_id: str, approval_data: ApprovalRequest):
    """
    Interrupt konumunda bekleyen grafı uyandırır (Resume).
    """
    logger.info(f"[{thread_id}] Kullanıcı Yanıtı Geldi: Onay={approval_data.is_approved}")
    _push_activity(thread_id, f"HITL yanıtı alındı: {'ONAY' if approval_data.is_approved else 'RED'}")
    
    config = {"configurable": {"thread_id": thread_id}}

    if _is_canceled(thread_id):
        logger.warning(f"[{thread_id}] Süreç daha önce iptal edilmiş, resume yapılmayacak.")
        _push_activity(thread_id, "Resume atlandı: thread iptal durumda.")
        return
    
    # Command(resume=) yollanarak duran graf tetiklenir ve kaldığı yerden devam eder.
    resume_command = Command(resume=approval_data.is_approved)
    
    try:
        for step in agent_app.stream(resume_command, config=config):
            if _is_canceled(thread_id):
                logger.warning(f"[{thread_id}] Resume sırasında iptal algılandı, stream durduruluyor.")
                cancel_analysis_task(thread_id)
                break

            for node_name, updates in step.items():
                logger.info(f"[{thread_id}] >>> Ajan Devam Ediyor: {node_name}")
                _push_activity(thread_id, f"Node işlendi: {node_name}")
                
        logger.info(f"[{thread_id}] Graf uyandırıldı ve süreç tamamen sonuçlandırıldı.")
        if not _is_canceled(thread_id):
            _push_activity(thread_id, "Resume akışı tamamlandı.")
    except Exception as e:
         logger.error(f"[{thread_id}] Uyandırma sırasında hata: {str(e)}")
         _push_activity(thread_id, f"Resume hatası: {str(e)}")

def get_thread_status(thread_id: str) -> ThreadStatusResponse:
    """
    PostgreSQL Saver (Checkpointer) üzerinden mevcut state'i okur.
    UI bu fonksiyonu tetikleyerek sürecin Interrupt'ta mı yoksa Çalışıyor mu olduğunu anlar.
    """
    config = {"configurable": {"thread_id": thread_id}}
    
    snapshot = agent_app.get_state(config)
    
    if not snapshot:
        return ThreadStatusResponse(
            thread_id=thread_id,
            status="failed",
            is_interrupted=False,
            pending_node=None,
            state=None
        )

    is_interrupted = len(snapshot.tasks) > 0 and snapshot.tasks[0].interrupts
    
    pending_node = snapshot.next[0] if snapshot.next else None
    
    state_values = snapshot.values

    if _is_canceled(thread_id) or state_values.get("credit_decision") == "CANCELED":
        status = "canceled"
        is_interrupted = False
    else:
        status = "completed" if len(snapshot.next) == 0 else "interrupted" if is_interrupted else "running"

    safe_state = AgentStateSchema(
        company_name=state_values.get("company_name", ""),
        financial_kpis=state_values.get("financial_kpis", []),
        market_sentiment=state_values.get("market_sentiment", []),
        audit_log=state_values.get("audit_log", []),
        loop_step=state_values.get("loop_step", 0),
        final_report=state_values.get("final_report", ""),
        credit_decision=state_values.get("credit_decision", "PENDING"),
        next_node=state_values.get("next_node", "orchestrator"),
        human_approval=state_values.get("human_approval")
    )
    
    return ThreadStatusResponse(
        thread_id=thread_id,
        status=status,
        is_interrupted=bool(is_interrupted),
        pending_node=pending_node,
        activity_log=_get_activity(thread_id),
        state=safe_state
    )
