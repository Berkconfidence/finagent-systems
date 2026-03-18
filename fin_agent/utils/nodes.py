# fin_agent/utils/nodes.py
from fin_agent.utils.state import SimpleState

def greeting_node(state: SimpleState):
    print("--- Greeting Node Çalışıyor ---")
    name = state.get("user_name", "Misafir")
    # State'e eklenecek yeni mesajı sözlük olarak döner
    return {"messages": [f"Merhaba {name}, sana nasıl yardımcı olabilirim?"]}

def logic_node(state: SimpleState):
    print("--- Logic Node Çalışıyor ---")
    return {"messages": ["Sistem analizleri tamamlandı."]}