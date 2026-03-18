# fin_agent/agent.py
from langgraph.graph import StateGraph, START, END
from fin_agent.utils.state import SimpleState
from fin_agent.utils.nodes import greeting_node, logic_node

# 1. Grafı State yapısıyla başlat
workflow = StateGraph(SimpleState)

# 2. Node'ları (fonksiyonları) ekle
workflow.add_node("greeter", greeting_node)
workflow.add_node("analyzer", logic_node)

# 3. Akışı (Edge) belirle
workflow.add_edge(START, "greeter")
workflow.add_edge("greeter", "analyzer")
workflow.add_edge("analyzer", END)

# 4. Derle (Compile)
app = workflow.compile()