from dotenv import load_dotenv
load_dotenv()

from fin_agent.agent import app

def main():
    initial_state = {
        "company_name": "TÜRK HAVA YOLLARI A.O.",
        "instructions": [],
        "messages": [],
        "financial_kpis": [],
        "market_sentiment": [],
        "audit_log": [],
        "loop_step": 0,
        "final_report": "",
        "credit_decision": "PENDING",
        "next_node": "orchestrator"
    }

    print(f"\n--- {initial_state['company_name']} İÇİN KREDİ RİSK ANALİZİ BAŞLATILIYOR ---\n")

    for step in app.stream(initial_state):
        for node_name, state_updates in step.items():
            print(f">>> [ {node_name.upper()} ] AKTİF")
            
            if node_name == "orchestrator":
                if "instructions" in state_updates and state_updates["instructions"]:
                    print(f"Strateji Çıktısı: {state_updates['instructions'][-1].content}\n")
            
            elif node_name == "financial_agent":
                if "financial_kpis" in state_updates:
                    print(f"Finans Verisi Analiz Edildi.")
            
            elif node_name == "market_agent":
                if "market_sentiment" in state_updates:
                    print(f"Piyasa Verisi Analiz Edildi.")
            
            elif node_name == "risk_auditor_agent":
                print(f"Denetçi Kararı: {state_updates.get('credit_decision', 'Bilinmiyor')}")
                if "audit_log" in state_updates and state_updates["audit_log"]:
                    print(f"Denetçi Notu: {state_updates['audit_log'][-1]}")
                print(f"Döngü Adımı/Artışı: +{state_updates.get('loop_step', 0)}\n")

    print("\n--- SÜREÇ TAMAMLANDI ---\n")

if __name__ == "__main__":
    main()
