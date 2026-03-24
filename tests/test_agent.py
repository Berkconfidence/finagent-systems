from dotenv import load_dotenv
load_dotenv()

from fin_agent.agent import app

def main():
    threads = ["test_kredi_analizi_001", "test_kredi_analizi_002"]

    for idx, thread_id in enumerate(threads):
        print(f"\n=======================================================")
        print(f"[{idx+1}. OTURUM] THREAD ID: {thread_id}")
        print(f"=======================================================\n")
        
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

        config = {
            "configurable": {
                "thread_id": thread_id
            }
        }

        for step in app.stream(initial_state, config=config):
            for node_name, state_updates in step.items():
                print(f">>> [ {node_name.upper()} ] AKTİF")
                
                if node_name == "orchestrator":
                    if "instructions" in state_updates and state_updates["instructions"]:
                        print(f"Orchestrator Mesajı:\n{state_updates['instructions'][-1].content}\n")
                
                elif node_name == "financial_agent":
                    if "messages" in state_updates:
                        print(f"{state_updates['messages'][-1].content}")
                
                elif node_name == "market_agent":
                    if "messages" in state_updates:
                        print(f"{state_updates['messages'][-1].content}")
                
                elif node_name == "risk_auditor_agent":
                    print(f"Denetçi Kararı: {state_updates.get('credit_decision', 'Bilinmiyor')}")
                    if "final_report" in state_updates and state_updates["final_report"]:
                        print(f"Rapor: {state_updates['final_report']}\n")

        print(f"\n--- {thread_id} SÜRECİ TAMAMLANDI ---\n")

if __name__ == "__main__":
    main()
