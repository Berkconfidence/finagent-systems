import json
import uuid
from loguru import logger
import grpc
from fin_proto import credit_score_pb2
from fin_proto import credit_score_pb2_grpc
from app.schemas.analysis import AnalysisRequest
from app.services.agent_service import (
    find_active_thread_for_company,
    get_thread_status,
    start_analysis_task,
)


def _to_json_str(data):
    try:
        return json.dumps(data, ensure_ascii=False) if data else "[]"
    except Exception:
        return "[]"


class CreditRiskGRPCServer(credit_score_pb2_grpc.CreditRiskServiceServicer):
    """
    gRPC Server sınıfımız. credit_score.proto'da tanımladığımız ve derlediğimiz
    'CreditRiskServiceServicer' sınıfını miras alarak içini dolduruyoruz.
    """

    async def StartAnalysis(self, request, context):
        """
        Dış dünyadan yeni analiz isteği geldiğinde tetiklenir.
        """
        company_name = (request.company_name or "").strip()
        logger.info(f"[gRPC] Yeni analiz talebi alındı: {company_name}")

        if not company_name:
             context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
             context.set_details("Şirket adı (company_name) zorunludur.")
             return credit_score_pb2.AnalysisResponse()

        try:
            existing_thread = find_active_thread_for_company(company_name)
            if existing_thread:
                state_obj = getattr(existing_thread, "state", None)
                return credit_score_pb2.AnalysisResponse(
                    thread_id=existing_thread.thread_id,
                    company_name=getattr(state_obj, "company_name", company_name) if state_obj else company_name,
                    credit_decision=getattr(state_obj, "credit_decision", "PENDING") if state_obj else "PENDING",
                    final_report=getattr(state_obj, "final_report", "") if state_obj else "",
                    financial_kpis_json=_to_json_str(getattr(state_obj, "financial_kpis", [])) if state_obj else "[]",
                    market_sentiment_json=_to_json_str(getattr(state_obj, "market_sentiment", [])) if state_obj else "[]",
                    audit_log_json=_to_json_str(getattr(state_obj, "audit_log", [])) if state_obj else "[]",
                    waiting_for_human=bool(getattr(existing_thread, "is_interrupted", False)),
                )

            thread_id = str(uuid.uuid4())
            analysis_request = AnalysisRequest(company_name=company_name)

            import threading
            threading.Thread(target=start_analysis_task, args=(thread_id, analysis_request), daemon=True).start()

            return credit_score_pb2.AnalysisResponse(
                thread_id=thread_id,
                company_name=company_name,
                credit_decision="PENDING",
                final_report="Analiz süreci kuyruğa alındı.",
                financial_kpis_json="[]",
                market_sentiment_json="[]",
                audit_log_json="[]",
                waiting_for_human=False
            )

        except Exception as e:
            logger.error(f"[gRPC] Hata - StartAnalysis: {str(e)}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Sunucu hatası: {str(e)}")
            return credit_score_pb2.AnalysisResponse()


    async def GetAnalysisStatus(self, request, context):
        """
        İstemci "Bu thread (istek) ne oldu?" diye sorduğunda DB'ye (LangGraph Store) bakıp cevap döner.
        """
        thread_id = request.thread_id
        
        if not thread_id:
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details("thread_id zorunludur.")
            return credit_score_pb2.AnalysisResponse()

        try:
            state_data = get_thread_status(thread_id)

            if not state_data:
                context.set_code(grpc.StatusCode.NOT_FOUND)
                context.set_details("Böyle bir thread bulunamadı.")
                return credit_score_pb2.AnalysisResponse()

            status = getattr(state_data, "status", "PENDING")
            state_obj = getattr(state_data, "state", None)

            company_val = getattr(state_obj, "company_name", "") if state_obj else ""
            decision_val = getattr(state_obj, "credit_decision", "PENDING") if state_obj else "PENDING"
            report_val = getattr(state_obj, "final_report", "") if state_obj else ""
            kpi_val = _to_json_str(getattr(state_obj, "financial_kpis", [])) if state_obj else "[]"
            market_val = _to_json_str(getattr(state_obj, "market_sentiment", [])) if state_obj else "[]"
            audit_val = _to_json_str(getattr(state_obj, "audit_log", [])) if state_obj else "[]"
            waiting_val = getattr(state_data, "is_interrupted", False)

            return credit_score_pb2.AnalysisResponse(
                thread_id=thread_id,
                company_name=company_val,
                credit_decision=decision_val,
                final_report=report_val,
                financial_kpis_json=kpi_val,
                market_sentiment_json=market_val,
                audit_log_json=audit_val,
                waiting_for_human=waiting_val
            )

        except Exception as e:
            logger.error(f"[gRPC] Hata - GetAnalysisStatus: {str(e)}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Sunucu hatası: {str(e)}")
            return credit_score_pb2.AnalysisResponse()
