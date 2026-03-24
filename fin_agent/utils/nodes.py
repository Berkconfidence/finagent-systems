import os
import json
from langchain_core.messages import AIMessage, SystemMessage, HumanMessage, ToolMessage
from langchain_google_vertexai import ChatVertexAI
from fin_agent.utils.state import AgentState
from fin_agent.utils.tools import get_pdf_base64, search_market_data
from langgraph.store.base import BaseStore # Bunu import edin


llm = ChatVertexAI(model="gemini-2.5-flash", temperature=0.2)

def orchestrator(state: AgentState, store: BaseStore):
    """
    Kredi analiz sürecini başlatan, risk parametrelerini belirleyen 
    ve iş akışını yöneten ana orkestratör düğümü.
    """
    
    company = state.get("company_name", "Bilinmeyen Şirket")
    safe_company_name = company.replace(".", "").strip()
    loop_step = state.get("loop_step", 0)
    
    past_memory = store.get(namespace=("companies", safe_company_name), key="last_credit_decision")
    
    if past_memory and loop_step == 0:
        decision = past_memory.value.get("decision")
        reason = past_memory.value.get("reason")
        msg = f"[SKIP_ANALYSIS] HAFIZA BULUNDU: {company} için daha önce analiz yapılmış.\nSon Karar: {decision}\nGerekçe: {reason}\nTekrar analiz yapılmayacaktır."
        return {"instructions": [AIMessage(content=msg)]}

    audit_logs = state.get("audit_log", [])
    latest_audit = audit_logs[-1] if audit_logs else None
    
    context_str = f"CONTEXT: {company} firması için kurumsal kredi risk analizi süreci başlatılıyor."
    if latest_audit:
        context_str += f"""
        
        DİKKAT - DENETÇİDEN (AUDITOR) REVİZYON TALEBİ GELDİ:
        Bu bir tekrar değerlendirme döngüsüdür. Önceki analizlerde denetçi şu sorunu tespit etti:
        '{latest_audit}'
        
        GÖREVİN: Lütfen ajanlar için hazırlayacağın yeni analiz planını, DOĞRUDAN denetçinin bu eleştirilerini giderecek odak noktalarıyla kurgula. Sistemin en fazla 3 deneme hakkı vardır, analiz ajanlarını tam verimle çözüm üretmeye zorla!
        """
    
    system_prompt = f"""ROLE: Kurumsal bir finans kuruluşunun Kredi Komitesi Başkanı ve Kıdemli AI Mimarı.
    {context_str}

    GOAL: 
    1. Analiz kapsamını belirle (Finansal KPI'lar ve Piyasa verileri).
    2. Görevleri 'financial_agent' ve 'market_agent' arasında paylaştır.
    3. Analiz planını rasyonel bir temele oturt.

    KNOWLEDGE BASE (Expertise):
    - IFRS Standartları ve Bankacılık Düzenleme Denetleme Kurumu (BDDK) rasyoları.
    - Sektörel volatilite analizi ve duyarlılık testleri.

    OUTPUT REQUIREMENTS:
    Yanıtını mutlaka aşağıdaki JSON formatında vermelisin. Başka açıklama yapma.
    {{
        "plan": "Ajanlara verilecek detaylı stratejik talimat metni. (Lütfen sadece düz metin (string) yazın, iç içe JSON objeleri kullanmayın.)",
        "reasoning": "Neden bu ajanlar seçildi? Hangi risklere odaklanılacak?",
        "next_node": "financial_agent" 
    }}
    """

    user_prompt = f"Analiz edilecek hedef şirket: {company}. Lütfen görev dağılımını ve stratejik planı hazırla."

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt)
    ]

    response = llm.invoke(messages)

    try:
        cleaned_text = response.content.replace("```json", "").replace("```", "").strip()
        decision = json.loads(cleaned_text)
    except Exception as e:
        decision = {
            "plan": f"Hata: JSON parse edilemedi ({str(e)}). Manuel planlama devreye alınıyor.",
            "next_node": "financial_agent"
        }

    analysis_plan_msg = (
        f"--- ORCHESTRATOR ANALIZ PLANI ---\n"
        f"Strateji: {decision.get('plan')}\n"
        f"Gerekçe: {decision.get('reasoning')}"
    )

    return {"instructions": [AIMessage(content=analysis_plan_msg)]}

def financialAgent(state: AgentState):
    """Finansal verileri analiz eden ve KPI'ları çıkaran ajan."""

    root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    pdf_path = os.path.join(root_dir, "sample_statement.pdf")

    pdf_base64 = get_pdf_base64(pdf_path)

    company_name = state.get("company_name", "Bilinmeyen Şirket")
    
    inst_list = state.get("instructions", [])
    orchestrator_instruction = inst_list[-1].content if inst_list else "Talimat yok."
    
    if "[SKIP_ANALYSIS]" in orchestrator_instruction:
        return {
            "messages": [AIMessage(content="Hafızada bulunduğu için finansal analiz atlandı.")]
        }
    
    system_prompt = f"""Sen kıdemli bir kurumsal kredi analistisin (Senior Credit Underwriter).
    Orkestratör Sorumlusu tarafından sana iletilen analiz stratejisi ve odaklanman gereken talimatlar şunlardır:
    --- ORKESTRATÖR TALİMATI ---
    {orchestrator_instruction}
    ----------------------------

    Yukarıdaki stratejik odağı dikkate alarak iletilen verileri incele ve KESİNLİKLE aşağıdaki şemaya uygun, sadece saf JSON formatında çıktı ver. Başka hiçbir açıklama metni ekleme.
    Eğer oranlar (örneğin current_ratio, debt_to_equity vb.) tablolarda doğrudan yazmıyorsa, lütfen bilançodaki ve gelir tablosundaki alt kalemleri (Dönen Varlıklar, Kısa Vadeli Yabancı Kaynaklar, Borçlar, Özkaynak vb.) bularak kendin HESAPLA. Gerekli tüm matematiksel işlemleri yap. Sadece hesaplama için gereken alt kalemler de yoksa veya şirket verileri net değilse `null` ata. Uydurma veri üretme.

    Beklenen JSON yapısı:
    {{
    "company_info": {{
        "company_name": "string",
        "period": "string"
    }},
    "liquidity_metrics": {{
        "current_ratio": float,          // Dönen Varlıklar / Kısa Vadeli Yabancı Kaynaklar
        "quick_ratio": float             // (Dönen Varlıklar - Stoklar) / Kısa Vadeli Yabancı Kaynaklar
    }},
    "leverage_and_debt": {{
        "total_assets": float,
        "total_debt": float,             // Kısa + Uzun Vadeli Finansal Borçlar
        "total_equity": float,           // Özkaynaklar
        "debt_to_equity": float,         // Toplam Borç / Özkaynak
        "interest_coverage_ratio": float // FAVÖK (EBITDA) / Finansman Giderleri (Faiz)
    }},
    "profitability_metrics": {{
        "revenue": float,                // Satış Gelirleri
        "gross_margin": float,           // Brüt Kar / Satış Gelirleri
        "ebitda": float,                 // Faiz, Amortisman ve Vergi Öncesi Kar
        "ebitda_margin": float,          // FAVÖK / Satış Gelirleri
        "net_profit": float              // Net Dönem Karı
    }},
    "cash_flow_metrics": {{
        "operating_cash_flow": float,    // İşletme Faaliyetlerinden Sağlanan Nakit
        "free_cash_flow": float          // Serbest Nakit Akışı
    }}
    }}
    """

    user_prompt = f"Görev: {company_name} firmasının aşağıdaki dosyada sunulan finansal tablolarını analiz et."
    
    content_parts = [
        {"type": "text", "text": user_prompt},
        {"type": "file", "base64": pdf_base64, "mime_type": "application/pdf"}
    ]
    
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=content_parts)
    ]
    
    response = llm.invoke(messages)
    
    try:
        cleaned_text = response.content.replace("```json", "").replace("```", "").strip()
        raw_analysis = json.loads(cleaned_text)
    except Exception as e:
        raw_analysis = {"error": f"JSON Parse veya çağırma hatası: {str(e)}"}

    return {
        "financial_kpis": [raw_analysis],
        "messages": [AIMessage(content="Finansal analiz tamamlandı, KPI'lar çıkarıldı.")]
    }

def marketAgent(state: AgentState):
    """Market verilerini analiz eden ajan"""

    company_name = state.get("company_name", "Bilinmeyen Şirket")
    
    inst_list = state.get("instructions", [])
    orchestrator_instruction = inst_list[-1].content if inst_list else "Talimat yok."

    if "[SKIP_ANALYSIS]" in orchestrator_instruction:
        return {
            "messages": [AIMessage(content="Hafızada bulunduğu için piyasa analizi atlandı.")]
        }

    system_prompt = f"""Sen kıdemli bir Piyasa Riski Analistisin (Senior Market Risk Analyst / Piyasanın Sesi).
    Ayrıca Orkestratör Sorumlusu tarafından sana iletilen analiz stratejisi ve odaklanman gereken talimatlar şunlardır:
    --- ORKESTRATÖR TALİMATI ---
    {orchestrator_instruction}
    ----------------------------

    Analiz yapmak için İLK ÖNCE güncel piyasa verilerini 'search_market_data' aracını kullanarak çekmelisin.
    Eğer veriyi çektiysen, KESİNLİKLE aşağıdaki şemaya uygun, sadece saf JSON formatında çıktı ver. Başka hiçbir açıklama metni ekleme.

    Beklenen JSON yapısı:
    {{
    "market_analysis": {{
        "company_name": "{company_name}",
        "sector_risk_score": int,          // 1 ile 100 arası risk puanı
        "sentiment": "string",             // "POSITIVE", "NEUTRAL", veya "NEGATIVE"
        "key_risks": ["string"],           // Sektörel veya firmaya özgü tespit edilen en kritik riskler (Max 4 madde)
        "competitor_analysis": "string",   // Rakiplere kıyasla genel pazar konumu ve rekabet gücü özeti
        "critical_news_summary": "string", // Haber akışının kısa bir özeti ve şirkete olası etkisi
        "recommendation_note": "string"    // Analist notu
    }}
    }}
    """

    user_prompt = f"Görev: {company_name} firmasının güncel haber akışını, sektördeki makroekonomik riskleri ve rakip durumunu değerlendirmek."

    llm_with_tools = llm.bind_tools([search_market_data])
    
    messages_to_send = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt)
    ]
    
    ai_msg = llm_with_tools.invoke(messages_to_send)
    
    messages_to_send.append(ai_msg)
    
    if ai_msg.tool_calls:
        for tool_call in ai_msg.tool_calls:
            if tool_call["name"] == "search_market_data":
                args = tool_call["args"]
                search_results = search_market_data.invoke(args)
                
                tool_msg = ToolMessage(
                    content=search_results, 
                    tool_call_id=tool_call["id"]
                )
                messages_to_send.append(tool_msg)
        
        final_response = llm.invoke(messages_to_send)
        try:
            cleaned_text = final_response.content.replace("```json", "").replace("```", "").strip()
            final_response_dict = json.loads(cleaned_text)
        except Exception:
            final_response_dict = {"error": "JSON parse edilemedi"}
    else:
        try:
            cleaned_text = ai_msg.content.replace("```json", "").replace("```", "").strip()
            final_response_dict = json.loads(cleaned_text)
        except Exception:
            final_response = llm.invoke(messages_to_send)
            try:
                cleaned_text = final_response.content.replace("```json", "").replace("```", "").strip()
                final_response_dict = json.loads(cleaned_text)
            except Exception:
                final_response_dict = {"error": "JSON parse edilemedi"}

    try:
        raw_analysis = final_response_dict if isinstance(final_response_dict, dict) else json.loads(final_response_dict)
    except Exception as e:
        raw_analysis = {"error": f"JSON Parse hatası: {str(e)}"}

    return {
        "market_sentiment": [raw_analysis],
        "messages": [AIMessage(content="Piyasa, haber akışı ve sektörel risk analizi tamamlandı.")]
    }

def riskAuditorAgent(state: AgentState, store: BaseStore):
    """
    Finansal ve piyasa verilerini banka kredi politikasıyla karşılaştırıp 
    nihai kararı veren veya revizyon isteyen denetçi ajan.
    """
    
    company_name = state.get("company_name", "Bilinmeyen Şirket")
    safe_company_name = company_name.replace(".", "").strip()
    financial_data = state.get("financial_kpis", [])[-1] if state.get("financial_kpis") else {}
    market_data = state.get("market_sentiment", [])[-1] if state.get("market_sentiment") else {}
    loop_state = state.get("loop_step", 0)
    audit_logs = state.get("audit_log", [])

    inst_list = state.get("instructions", [])
    orchestrator_instruction = inst_list[-1].content if inst_list else ""
    
    if "[SKIP_ANALYSIS]" in orchestrator_instruction:
        past_memory = store.get(namespace=("companies", safe_company_name), key="last_credit_decision")
        decision = past_memory.value.get("decision") if past_memory else "UNKNOWN"
        reason = past_memory.value.get("reason") if past_memory else "UNKNOWN"
        return {
            "credit_decision": decision,
            "final_report": f"Geçmiş hafızadan getirildi. Karar: {decision}\nGerekçe: {reason}",
            "next_node": "END",
            "messages": [AIMessage(content=f"Auditor: Hafızadan karar onandı: {decision}")]
        }

    history_str = ""
    if audit_logs:
        logs_joined = "\n".join([f"- Döngü {i+1}: {log}" for i, log in enumerate(audit_logs)])
        history_str = f"""
        GEÇMİŞ REVİZYON TALEPLERİN (AUDIT LOG GEÇMİŞİ):
        {logs_joined}

        DİKKAT - DÖNGÜ ENGELLEME KURALI:
        Yukarıdaki geçmiş taleplerine bak. Eğer daha önceki bir döngüde "X verisi eksik", "Y hesaplanamamış" diyerek eksik verilerden dolayı revizyon (REVISION_REQUIRED) istediysen ve sana gelen yeni 'financial_data' içinde bu alanlar HALA eksik/null ise, demek ki analiz edilen dökümanlarda bu veriler KESİNLİKLE YOKTUR. Ajanlar aynı PDF'i inceliyor, olmayan veriyi var edemezler.
        Bu durumda, AYNI EKSİK BİLGİ İÇİN TEKRARDAN "REVISION_REQUIRED" KULLANAMAZSIN! Eksik verilerin varlığını kabul et ve doğrudan elindeki mevcut verilere (örneğin mevcut current_ratio'ya vb.) veya sektör risklerine bakarak "APPROVED" ya da "REJECTED" kararı ver. Paranı/token'ı boşa harcama!
        """

    credit_policy = """
    1. Cari Oran (Current Ratio) > 1.2 olmalıdır. Aksi halde likidite riski vardır.
    2. Borç / Özsermaye (Debt to Equity) < 4.0 olmalıdır. Aşarsa yüksek kaldıraç riski yaratır.
    3. Faiz Karşılama Oranı (Interest Coverage Ratio) > 1.5 olmalıdır. Borç ödeme kapasitesi için kritiktir.
    4. Sektör Risk Puanı > 70 veya Haber Akışında Belirgin Bir 'NEGATIVE' sentiment varsa, şirketin faaliyet riski yüksektir; 'REVISION_REQUIRED' denilerek daha detaylı inceleme talep edilmelidir.
    5. Güçlü Operasyonel Nakit Akışı veya FAVÖK Marjı, makroekonomik riskleri bir nebze hafifletebilir ancak tamamen silmez.
    """

    system_prompt = f"""Sen kurumun Kıdemli Kredi Risk Denetçisisin (Senior Risk Auditor).
    MEVCUT DURUM:
    Şu anda analiz döngüsünün {loop_state}. adımındasın. Maximum döngü limiti 1'dir. 
    EĞER BU ADIM >= 2 İSE, 'REVISION_REQUIRED' seçeneğini KESİNLİKLE KULLANAMAZSIN. Ya 'APPROVED' ya da 'REJECTED' kararı vermek ZORUNDASIN.

    KURALLAR:
    {credit_policy}

    SENİN BİLGİ KAYNAKLARIN:
    {history_str}

    KARAR STRATEJİSİ VE ÇIKTI FORMATI:
    1. Verileri harmanla: Kar çok iyi ama piyasada çok büyük riskler varsa ve (loop_step < 3) ise "REVISION_REQUIRED" kararı ver ve analizde spesifik neyin eksik/çelişkili olduğunu "audit_note" içinde açıkla.
    2. Eğer metrikler politikaya açıkça ters düşüyor ve kabul edilemez riskler barındırıyorsa "REJECTED".
    3. Eğer şirket genel hatlarıyla sağlıklıysa ve riskler tolere edilebilirse "APPROVED".
    4. "next_node" değeri kararına bağlıdır. Karar "REVISION_REQUIRED" ise 'orchestrator' olmalıdır (çünkü ajanları yeniden paralel başlatacağız). Karar "APPROVED" veya "REJECTED" ise 'END' olmalıdır.
    5. YANITINI KESİNLİKLE AŞAĞIDAKİ JSON ŞEMASIYLA VER:

    {{
        "decision": "APPROVED" | "REJECTED" | "REVISION_REQUIRED",
        "audit_note": "Ajanlara yönelik eleştiri veya onay gerekçesi...",
        "summary_report": "Kredi komitesine sunulacak derinlemesine yönetici özeti...",
        "next_node": "orchestrator" | "END"
    }}
    """

    user_prompt = f"""Görevin: Finansal ajan ve piyasa ajanından gelen aşağıdaki ham KPI verilerini Banka Kredi Politikası ile çapraz doğrulamak ve son kredi kararını (veya ek analiz talebini) vermektir.
    ANALİZ EDİLECEK VERİLER:
    - Şirket Adı: {company_name}
    - Finans Ajanından Gelen Veriler (KPIs): {json.dumps(financial_data, ensure_ascii=False)}
    - Piyasa Ajanından Gelen Veriler (Market & Sentiment): {json.dumps(market_data, ensure_ascii=False)}
    """

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt)
    ]

    response = llm.invoke(messages)
    
    try:
        cleaned_text = response.content.replace("```json", "").replace("```", "").strip()
        raw_analysis = json.loads(cleaned_text)
    except Exception as e:
        raw_analysis = {
            "decision": "REJECTED",
            "audit_note": f"Sistem hatası veya JSON parse edilemedi: {str(e)}",
            "summary_report": "Otomatik red kararı - Analiz tamamlanamadı.",
            "next_node": "END"
        }

    # Eğer model kurala uymayıp loop>=3 iken hala revision dönerse (Hallucination önlemi)
    decision = raw_analysis.get("decision", "REJECTED")
    if loop_state >= 2 and decision == "REVISION_REQUIRED":
        decision = "REJECTED"
        raw_analysis["decision"] = decision
        raw_analysis["audit_note"] = "Maximum analiz limitine ulaşıldı, zorunlu olarak karar mekanizması işletildi ve güvenlik nedeniyle Reddedildi."
        raw_analysis["next_node"] = "END"


    store.put(
        namespace=("companies", safe_company_name),
        key="last_credit_decision",
        value={"decision": decision, "reason": raw_analysis.get("audit_note", "Belirtilmedi")}
    )

    return {
        "credit_decision": decision,
        "audit_log": [raw_analysis.get("audit_note", "No note")],
        "final_report": raw_analysis.get("summary_report", ""),
        "instructions": [AIMessage(content=f"DENETÇİ NOTU: {raw_analysis.get('audit_note')}")],
        "next_node": raw_analysis.get("next_node", "END"),
        "loop_step": 1,
        "messages": [AIMessage(content=f"Auditor kararı: {decision}")]
    }

def routeReport(state: AgentState):
    """
    Nihai karara veya revizyon isteğine göre yönlendiren koşullu fonksiyon.
    Bu bir node (düğüm) değil, bir Edge (kenar) koşuludur (Conditional Edge).
    Graph'a "Hangi yola gideyim?" sorusunun cevabını string (düğüm adı) olarak döner.
    """
    next_node = state.get("next_node", "END")
    
    if next_node not in ["orchestrator", "END"]:
        return "END"
        
    return next_node
