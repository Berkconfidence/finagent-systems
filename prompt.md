# Diagnostic Request: FinAgent-360 Performance Degradation & 429 Errors

## 1. Context & Environment
I am developing an Agentic AI system called **FinAgent-360** using **LangGraph** and **Vertex AI (Gemini 2.5 Flash)**. The system is designed to perform credit risk analysis on corporate entities.

**Environment Details:**
- **OS:** Ubuntu 24.04
- **Python:** 3.12.3 (.venv)
- **Infrastructure:** Dockerized FastAPI app, gRPC, and Qdrant DB.
- **LLM:** Gemini 2.5 Flash via `langchain-google-vertexai` (deprecated) or `ChatVertexAI`.
- **Input:** A 26-page financial PDF (converted to images for multi-modal analysis).

## 2. The Problem
The system has experienced a severe performance drop. Initially, a full analysis took approximately **5 minutes**. Now, it exceeds **30 minutes** and frequently crashes or hangs. I am also being bombarded with **429 Resource Exhausted** errors.

### Recent Execution Logs:
```text
"(.venv) berk@berk:~/finagent-systems$ PYTHONPATH=. python tests/test_agent.py

/home/berk/finagent-systems/fin_agent/utils/nodes.py:10: LangChainDeprecationWarning: The class `ChatVertexAI` was deprecated in LangChain 3.2.0 and will be removed in 4.0.0. An updated version of the class exists in the `langchain-google-genai package and should be used instead. To use it run `pip install -U `langchain-google-genai` and import as `from `langchain_google_genai import ChatGoogleGenerativeAI``.

  llm = ChatVertexAI(model="gemini-2.5-flash", temperature=0.2)

=======================================================
[1. OTURUM] THREAD ID: test_kredi_analizi_001
=======================================================

>>> [ ORCHESTRATOR ] AKTİF

Orchestrator Mesajı:

--- ORCHESTRATOR ANALIZ PLANI ---

Strateji: Kredi Komitesi olarak, TÜRK HAVA YOLLARI A.O. için kapsamlı bir kurumsal kredi risk analizi başlatılmıştır. Bu analiz, şirketin finansal sağlığını, operasyonel dayanıklılığını ve piyasa koşullarına adaptasyon yeteneğini değerlendirmeyi amaçlamaktadır. Görev dağılımı ve stratejik talimatlar aşağıdaki gibidir:

**financial_agent için Talimatlar:**

1.  **Veri Toplama:** TÜRK HAVA YOLLARI A.O.'nun son 5 yıllık bağımsız denetimden geçmiş finansal tablolarını (Bilanço, Gelir Tablosu, Nakit Akış Tablosu, Özkaynak Değişim Tablosu) ve dipnotlarını temin et.

2.  **IFRS Uyumluluğu ve Muhasebe Politikaları:** Finansal tabloların IFRS standartlarına uygunluğunu teyit et. Özellikle IFRS 16 (Kiralama İşlemleri) gibi havacılık sektörünü etkileyen önemli muhasebe politikalarının şirketin finansal görünümü üzerindeki etkilerini analiz et.

3.  **Finansal Oran Analizi:** Aşağıdaki temel finansal rasyoları hesapla ve trend analizini yap:

    *   **Karlılık:** Brüt Kar Marjı, Faaliyet Kar Marjı, Net Kar Marjı, FAVÖK Marjı, ROA, ROE.

    *   **Likidite:** Cari Oran, Likidite Oranı (Asit Test Oranı), Nakit Oranı.

    *   **Kaldıraç/Borçluluk:** Finansal Kaldıraç Oranı, Borç/Özkaynak Oranı, Net Borç/FAVÖK, Faiz Karşılama Oranı.

    *   **Faaliyet Etkinliği:** Alacak Devir Hızı, Aktif Devir Hızı.

4.  **Nakit Akış Analizi:** Faaliyetlerden, yatırım ve finansman faaliyetlerinden kaynaklanan nakit akışlarını detaylı incele. Serbest Nakit Akışı (FCF) hesaplaması yaparak şirketin borç ödeme kapasitesini ve büyüme potansiyelini değerlendir.

5.  **BDDK Rasyoları:** Bankacılık Düzenleme ve Denetleme Kurumu (BDDK) tarafından belirlenen ilgili rasyoları (örneğin, borç servis karşılama oranı, kaldıraç limitleri) şirketin finansal verileri üzerinden hesapla ve yorumla.

6.  **Tarihsel Performans ve Projeksiyon Girdileri:** Son 5 yıllık finansal performansın detaylı bir trend analizini sun. `market_agent` tarafından sağlanacak senaryo analizleri için finansal modelleme girdilerini (gelir ve gider kalemlerinin esneklik katsayıları vb.) hazırla.



**market_agent için Talimatlar:**

1.  **Sektörel Analiz:** Küresel ve yerel havacılık sektörünün mevcut durumunu, büyüme beklentilerini, rekabet yoğunluğunu (Porter'ın 5 Gücü analizi dahil), giriş engellerini ve teknolojik gelişmeleri değerlendir. IATA raporları ve Sivil Havacılık Genel Müdürlüğü verilerini kullan.

2.  **Makroekonomik Faktörler:** Türkiye ve THY'nin ana faaliyet gösterdiği pazarlardaki GSYH büyümesi, enflasyon, döviz kuru oynaklığı, faiz oranları gibi makroekonomik göstergelerin yolcu ve kargo talebi ile şirketin maliyet yapısı üzerindeki etkilerini analiz et.

3.  **Yakıt Fiyatları Volatilitesi:** Küresel petrol fiyatlarındaki (Brent, WTI) değişimlerin THY'nin operasyonel maliyetleri üzerindeki etkisini incele. Şirketin yakıt hedging stratejilerini ve bunların etkinliğini değerlendir.

4.  **Jeopolitik ve Operasyonel Riskler:** Bölgesel çatışmalar, terör olayları, salgın hastalıklar (geçmiş COVID-19 etkileri ve gelecekteki potansiyel riskler), seyahat kısıtlamaları gibi jeopolitik ve operasyonel risklerin yolcu talebi, rota kısıtlamaları ve sigorta maliyetleri üzerindeki etkilerini analiz et.

5.  **Regülasyon ve Çevresel Faktörler:** Sivil havacılık otoritelerinin düzenlemeleri, karbon emisyon hedefleri, çevresel vergiler ve bunların şirketin operasyonel maliyetleri ve yatırım planları üzerindeki etkilerini değerlendir.

6.  **Talep ve Kapasite Analizi:** Yolcu ve kargo taşımacılığı talebindeki trendleri, mevsimselliği, kapasite kullanım oranlarını ve doluluk oranlarını incele. THY'nin filo yapısı ve genişleme planlarını değerlendir.

7.  **Duyarlılık Testleri ve Senaryo Analizi:** `financial_agent`'tan alınacak girdilerle birlikte, aşağıdaki senaryoların şirketin finansal performansı üzerindeki etkilerini modelle:

    *   **Olumsuz Senaryo (Stres Testi):** Yakıt fiyatlarında %X artış, yolcu sayısında %Y düşüş, döviz kurunda %Z değer kaybı, jeopolitik gerilimlerin artması.

    *   **Orta Senaryo:** Mevcut makroekonomik ve sektörel trendlerin devamı.

    *   **İyimser Senaryo:** Küresel ekonomide toparlanma, yakıt fiyatlarında istikrar/düşüş, yolcu talebinde artış.

8.  **Rakip Analizi:** Bölgesel ve küresel rakiplerin finansal ve operasyonel performansları ile THY'nin karşılaştırmalı analizini sun.

Gerekçe: Bu görev dağılımı, her bir ajanın uzmanlık alanını en verimli şekilde kullanmak üzere tasarlanmıştır. `financial_agent`, şirketin içsel finansal sağlığını, muhasebe standartlarına uygunluğunu ve BDDK rasyoları gibi düzenleyici gereklilikleri titizlikle analiz edecektir. Bu, şirketin geçmiş performansını ve mevcut finansal yapısını objektif bir şekilde ortaya koyacaktır. `market_agent` ise, havacılık sektörünün doğası gereği yüksek volatiliteye sahip dışsal faktörleri (yakıt fiyatları, jeopolitik riskler, makroekonomik koşullar, rekabet) değerlendirerek, şirketin bu risklere karşı ne kadar dayanıklı olduğunu ve gelecekteki potansiyelini ortaya koyacaktır. Bu iki ajanın entegre çalışması, hem şirketin kendi finansal gücünü hem de içinde bulunduğu piyasa ve sektör koşullarını dikkate alan bütünsel bir kredi risk değerlendirmesi sağlayacaktır. Odaklanılacak temel riskler şunlardır:

*   **Finansal Riskler:** Likidite yetersizliği, aşırı borçluluk, karlılıkta sürdürülebilirlik sorunları, nakit akışı zayıflığı.
*   **Operasyonel Riskler:** Yakıt fiyatlarındaki öngörülemeyen artışlar, jeopolitik istikrarsızlık ve salgın hastalıklar nedeniyle operasyonel kesintiler veya talep düşüşleri, döviz kuru dalgalanmalarının maliyet ve gelirler üzerindeki etkisi.
*   **Piyasa Riskleri:** Küresel ve yerel ekonomik durgunluklar nedeniyle yolcu ve kargo talebinde düşüş, artan rekabet baskısı, çevresel düzenlemelerin getirdiği ek maliyetler.

Bu yaklaşım, TÜRK HAVA YOLLARI A.O. gibi büyük ve stratejik bir şirketin kredi riskini çok boyutlu olarak ele alarak, olası zayıflıkları ve güçlü yönleri kapsamlı bir şekilde belirlememizi sağlayacaktır.

Retrying langchain_google_vertexai.chat_models._completion_with_retry.<locals>._completion_with_retry_inner in 4 seconds as it raised ResourceExhausted: 429 Resource exhausted. Please try again later. Please refer to https://cloud.google.com/vertex-ai/generative-ai/docs/error-code-429 for more details..

Retrying langchain_google_vertexai.chat_models._completion_with_retry.<locals>._completion_with_retry_inner in 4 seconds as it raised ResourceExhausted: 429 Resource exhausted. Please try again later. Please refer to https://cloud.google.com/vertex-ai/generative-ai/docs/error-code-429 for more details..

Retrying langchain_google_vertexai.chat_models._completion_with_retry.<locals>._completion_with_retry_inner in 4 seconds as it raised ResourceExhausted: 429 Resource exhausted. Please try again later. Please refer to https://cloud.google.com/vertex-ai/generative-ai/docs/error-code-429 for more details..

>>> [ MARKET_AGENT ] AKTİF
Piyasa, haber akışı ve sektörel risk analizi tamamlandı.
Retrying langchain_google_vertexai.chat_models._completion_with_retry.<locals>._completion_with_retry_inner in 4 seconds as it raised ResourceExhausted: 429 Resource exhausted. Please try again later. Please refer to https://cloud.google.com/vertex-ai/generative-ai/docs/error-code-429 for more details.."
```

## 3. Your Task (Investigation & Resolution)
You are acting as a Senior AI Site Reliability Engineer (SRE) and LangGraph Architect. Your goal is to diagnose the root cause of this degradation and the 429 errors without me providing the solution.

# Instructions for Analysis:
1. Analyze the Architecture: Review the provided nodes.py, agent.py, and tools.py in my workspace. Pay close attention to how the PDF images are handled and how many concurrent requests are being fired.
2. Evaluate Quota Usage: Investigate Vertex AI (Gemini 2.5 Flash) documentation for 2026. Determine the RPM (Requests Per Minute) and TPM (Tokens Per Minute) limits. Compare these against the current workload (26 pages + Orchestrator output).
3. Trace the Bottleneck: Identify why the system slowed down from 5 minutes to 30+ minutes despite the PDF size remaining constant. Is it a retry-loop, a memory leak, or a state management issue in LangGraph?
4. Multi-Modal Impact: Calculate the estimated token count for 26 high-resolution images being processed by a Vision-enabled LLM in parallel/sequence.
5. Propose a Technical Fix: Based on your findings, provide the necessary code changes to optimize the system, handle rate limiting (backoff/throttling), and resolve the deprecation warnings.