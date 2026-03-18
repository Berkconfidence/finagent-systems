from fastapi import FastAPI
# LangGraph objenizi farklı bir isimle içe aktarın (örneğin agent_app)
from fin_agent.agent import app as agent_app 

# Uvicorn'un çalıştıracağı asıl FastAPI uygulaması
app = FastAPI(title="FinAgent Systems API")

@app.get("/")
async def root():
    return {"message": "FinAgent API çalışıyor."}

@app.get("/invoke")
async def invoke_agent(query: str):
    # LangGraph ajanını burada çalıştırın
    # Mevcut state yapınıza göre input formatı (dict vb.) değişebilir
    result = agent_app.invoke({"input": query}) 
    return {"response": result}