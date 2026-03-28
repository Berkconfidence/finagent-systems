import grpc
import time
from loguru import logger

# Derlenmiş olan Protobuf ve gRPC modüllerini içeri aktarıyoruz
from fin_proto import credit_score_pb2
from fin_proto import credit_score_pb2_grpc

def run_grpc_test():
    """
    Sanki bankanın ana (Core) sunucusuymuşuz gibi bizim AI servisine bağlanıyoruz.
    """
    # 1. Hangi Kanala (Channel) ve Porta bağlanacağız?
    # Gerçek hayatta bu '10.0.0.5:50051' gibi AI Docker sunucusunun adresi olur.
    channel = grpc.insecure_channel('localhost:50051')
    
    # 2. Müşteri (Stub) Objesini Oluşturuyoruz.
    # Bu obje, sunucudaki .proto fonksiyonlarını yerel bir Python fonksiyonu gibi 
    # çalıştırmamızı sağlar. gRPC'nin harika yanı budur.
    stub = credit_score_pb2_grpc.CreditRiskServiceStub(channel)

    company_to_test = "TURK HAVA YOLLARI A.O."
    logger.info(f"== TEST 1: Yeni Analiz Başlatılıyor ({company_to_test}) ==")

    # StartAnalysis fonksiyonunu çağırıyoruz ve içerisine proto class'ının formatında Veri gönderiyoruz
    request = credit_score_pb2.AnalysisRequest(company_name=company_to_test)
    
    try:
        start_response = stub.StartAnalysis(request)
        thread_id = start_response.thread_id
        logger.success(f"Analiz Başlatıldı! Thread ID: {thread_id}")
        logger.info(f"Sunucudan ilk Dönüş Durumu: {start_response.credit_decision}")
        
    except grpc.RpcError as e:
        logger.error(f"Baglantı Hatası! Sunucu açık mı? Detay: {e.details()}")
        return

    # 3. Sistemin Arka Planda Analizi Bitirmesini / Human in the Loop kısmına gelmesini bekle
    # Normalde banka sistemi hemen kapatır. Ancak biz test için 10 saniye sonra ne olmuş diye bakacağız.
    logger.info("== TEST 2: Langgraph İşlemi İçin 10 Saniye Bekleniyor... ==")
    for i in range(10, 0, -1):
        print(f"Bekleniyor... {i} sn", end="\r")
        time.sleep(1)
    print("\n")

    logger.info(f"== TEST 3: Durum Sorgulama (Polling) İşlemi ==")
    status_request = credit_score_pb2.ThreadRequest(thread_id=thread_id)
    
    try:
        # GetAnalysisStatus'u çağırıyoruz
        status_response = stub.GetAnalysisStatus(status_request)
        
        logger.success("=== SUNUCU SON DURUM RAPORU ===")
        logger.info(f"Şirket: {status_response.company_name}")
        logger.info(f"Karar (Decision): {status_response.credit_decision}")
        logger.info(f"HITL Onayı Bekliyor Mu?: {status_response.waiting_for_human}")
        logger.info(f"Nihai Rapor Özeti:\n{status_response.final_report}")
        
    except grpc.RpcError as e:
        logger.error(f"Sorgu Hatası: {e.details()}")

if __name__ == "__main__":
    logger.info("gRPC Test İstekleri Başlıyor...")
    run_grpc_test()
