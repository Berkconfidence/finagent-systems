from langgraph.types import Command
import logging
from fin_agent.agent import app as agent_app, pool
from app.schemas.analysis import AnalysisRequest, ApprovalRequest
from app.schemas.status import ThreadStatusResponse, AgentStateSchema

logger = logging.getLogger(__name__)


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

def start_analysis_task(thread_id: str, request_data: AnalysisRequest):
    """
    Arka planda LangGraph analiz sürecini başlatır.
    FastAPI BackgroundTasks tarafından çağrılacaktır.
    """
    logger.info(f"[{thread_id}] Yeni analiz başlıyor: {request_data.company_name}")
    
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
            if "__interrupt__" in step:
                logger.warning(f"[{thread_id}] SÜREÇ İNSAN ONAYI İÇİN DURAKLATILDI (Interrupt)")
                break
                
            for node_name, updates in step.items():
                logger.info(f"[{thread_id}] >>> Ajan Tamamlandı: {node_name}")
                
        logger.info(f"[{thread_id}] Analiz süreci durdu (Bitti veya Kesintiye Uğradı).")
        
    except Exception as e:
        logger.error(f"[{thread_id}] Analiz sırasında hata: {str(e)}")

def resume_analysis_task(thread_id: str, approval_data: ApprovalRequest):
    """
    Interrupt konumunda bekleyen grafı uyandırır (Resume).
    """
    logger.info(f"[{thread_id}] Kullanıcı Yanıtı Geldi: Onay={approval_data.is_approved}")
    
    config = {"configurable": {"thread_id": thread_id}}
    
    # Command(resume=) yollanarak duran graf tetiklenir ve kaldığı yerden devam eder.
    resume_command = Command(resume=approval_data.is_approved)
    
    try:
        for step in agent_app.stream(resume_command, config=config):
            for node_name, updates in step.items():
                logger.info(f"[{thread_id}] >>> Ajan Devam Ediyor: {node_name}")
                
        logger.info(f"[{thread_id}] Graf uyandırıldı ve süreç tamamen sonuçlandırıldı.")
    except Exception as e:
         logger.error(f"[{thread_id}] Uyandırma sırasında hata: {str(e)}")

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
    
    status = "completed" if len(snapshot.next) == 0 else "interrupted" if is_interrupted else "running"
    
    pending_node = snapshot.next[0] if snapshot.next else None
    
    state_values = snapshot.values

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
        state=safe_state
    )
