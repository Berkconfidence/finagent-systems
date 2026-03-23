from langgraph.graph import StateGraph, START, END
from fin_agent.utils.state import AgentState
from fin_agent.utils.nodes import orchestrator, financialAgent, marketAgent, riskAuditorAgent, routeReport
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.store.memory import InMemoryStore

# 1. Grafı State yapısıyla başlat
workflow = StateGraph(AgentState)

# 2. Node'ları ekle
workflow.add_node("orchestrator", orchestrator)
workflow.add_node("financial_agent", financialAgent)
workflow.add_node("market_agent", marketAgent)
workflow.add_node("risk_auditor_agent", riskAuditorAgent)

# 3. Akışı belirle
workflow.add_edge(START, "orchestrator")
workflow.add_edge("orchestrator", "financial_agent")
workflow.add_edge("orchestrator", "market_agent")
workflow.add_edge(["financial_agent", "market_agent"], "risk_auditor_agent")
workflow.add_conditional_edges(
    "risk_auditor_agent", 
    routeReport,          
    {
        "orchestrator": "orchestrator", 
        "END": END
    }
)

checkpointer = InMemorySaver()
store = InMemoryStore()

# 4. Derle
app = workflow.compile(checkpointer=checkpointer, store=store)
