import os
import json
from langchain_core.messages import AIMessage, SystemMessage, HumanMessage, ToolMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from fin_agent.utils.state import AgentState
from fin_agent.utils.tools import pdf_to_images, search_market_data


llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.2)

def orchestrator(state: AgentState):
    """
    Kredi analiz sürecini başlatan, risk parametrelerini belirleyen 
    ve iş akışını yöneten ana orkestratör düğümü.
    """
    
    company = state.get("company_name", "Bilinmeyen Şirket")
    
    system_prompt = f"""
    ROLE: Kurumsal bir finans kuruluşunun Kredi Komitesi Başkanı ve Kıdemli AI Mimarı.
    CONTEXT: {company} firması için kurumsal kredi risk analizi süreci başlatılıyor.
    
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
        "plan": "Detaylı analiz stratejisi...",
        "reasoning": "Neden bu ajanlar seçildi? Hangi risklere odaklanılacak?",
        "next_node": "financial_agent" 
    }}
    """    

    user_prompt = f"Analiz edilecek hedef şirket: {company}. Lütfen görev dağılımını ve stratejik planı hazırla."

    structured_llm = llm.with_structured_output(method="json_mode")
    response_dict = structured_llm.invoke(system_prompt + "\n" + user_prompt)

    try:
        decision = response_dict if isinstance(response_dict, dict) else json.loads(response_dict)
    except Exception as e:
        decision = {
            "plan": "Hata: JSON parse edilemedi. Manuel planlama devreye alınıyor.",
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

    images = pdf_to_images(pdf_path)

    company_name = state.get("company_name", "Bilinmeyen Şirket")
    orchestrator_instruction = state.get("instructions", "Talimat yok")
    
    prompt = f"""
    Sen kıdemli bir kurumsal kredi analistisin (Senior Credit Underwriter).
    Görev: {company_name} firmasının aşağıda verilen finansal tablo görsellerini (Bilanço, Gelir Tablosu, Nakit Akış Tablosu) analiz etmek.
    
    Orkestratör Sorumlusu tarafından sana iletilen analiz stratejisi ve odaklanman gereken talimatlar şunlardır:
    --- ORKESTRATÖR TALİMATI ---
    {orchestrator_instruction}
    ----------------------------
    
    Yukarıdaki stratejik odağı dikkate alarak verileri incele ve KESİNLİKLE aşağıdaki şemaya uygun, sadece saf JSON formatında çıktı ver. Başka hiçbir açıklama metni ekleme.
    Eğer bir veriyi ya da oranı tablolardan hesaplayamıyor veya bulamıyorsan, değer olarak `null` ata. Uydurma veri üretme.
    
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
    
    content_parts = [{"type": "text", "text": prompt}]
    for img in images:
        content_parts.append({
            "type": "image_url", 
            "image_url": {"url": f"data:image/png;base64,{img}"}
        })
    
    message = HumanMessage(content=content_parts)
    
    structured_llm = llm.with_structured_output(method="json_mode")
    
    try:
        response_dict = structured_llm.invoke([message])
        raw_analysis = response_dict if isinstance(response_dict, dict) else json.loads(response_dict)
    except Exception as e:
        raw_analysis = {"error": f"JSON Parse veya çağırma hatası: {str(e)}"}

    return {
        "financial_kpis": [raw_analysis],
        "messages": [AIMessage(content="Finansal analiz tamamlandı, KPI'lar çıkarıldı.")]
    }

def marketAgent(state: AgentState):
    """Market verilerini analiz eden ajan"""

    company_name = state.get("company_name", "Bilinmeyen Şirket")
    orchestrator_instruction = state.get("instructions", "Talimat yok")

    prompt = f"""
    Sen kıdemli bir Piyasa Riski Analistisin (Senior Market Risk Analyst / Piyasanın Sesi).
    Görev: {company_name} firmasının güncel haber akışını, sektördeki makroekonomik riskleri ve rakip durumunu değerlendirmek.
    
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

    llm_with_tools = llm.bind_tools([search_market_data])
    
    ai_msg = llm_with_tools.invoke(prompt)
    
    messages_to_send = [HumanMessage(content=prompt), ai_msg]
    
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
        
        structured_llm = llm.with_structured_output(method="json_mode")
        final_response_dict = structured_llm.invoke(messages_to_send)
    else:
        try:
            final_response_dict = json.loads(ai_msg.content)
        except Exception:
            structured_llm = llm.with_structured_output(method="json_mode")
            final_response_dict = structured_llm.invoke(messages_to_send)

    try:
        raw_analysis = final_response_dict if isinstance(final_response_dict, dict) else json.loads(final_response_dict)
    except Exception as e:
        raw_analysis = {"error": f"JSON Parse hatası: {str(e)}"}

    return {
        "market_sentiment": [raw_analysis],
        "messages": [AIMessage(content="Piyasa, haber akışı ve sektörel risk analizi tamamlandı.")]
    }
