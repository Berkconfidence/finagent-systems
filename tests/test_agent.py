from dotenv import load_dotenv
load_dotenv()

from fin_agent.agent import app
from langgraph.types import Command

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
            "next_node": "orchestrator",
            "human_approval": None
        }

        config = {
            "configurable": {
                "thread_id": thread_id
            }
        }

        # İlk çalıştırma — interrupt'a kadar ilerler
        stream_input = initial_state

        while True:
            interrupted = False

            for step in app.stream(stream_input, config=config):
                # Interrupt kontrolü
                if "__interrupt__" in step:
                    interrupted = True
                    interrupt_data = step["__interrupt__"][0]
                    payload = interrupt_data.value

                    print(f"\n{'='*55}")
                    print(f"⚠️  HUMAN-IN-THE-LOOP: İnsan Onayı Bekleniyor")
                    print(f"{'='*55}")
                    print(f"Soru       : {payload.get('question', '')}")
                    print(f"AI Kararı  : {payload.get('auditor_decision', '')}")
                    print(f"Denetçi Notu: {payload.get('audit_note', '')}")
                    print(f"Özet Rapor : {payload.get('summary_report', '')}")
                    print(f"{'='*55}")

                    answer = input("\n✋ Bu kararı onaylıyor musunuz? (e/h): ").strip().lower()
                    is_approved = answer == "e"

                    print(f"\n{'→ Onaylandı ✅' if is_approved else '→ Reddedildi ❌'}")
                    print(f"Graf devam ettiriliyor...\n")

                    # Resume ile devam et
                    stream_input = Command(resume=is_approved)
                    break

                # Normal node çıktılarını işle
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

            if not interrupted:
                break

        print(f"\n--- {thread_id} SÜRECİ TAMAMLANDI ---\n")

if __name__ == "__main__":
    main()
