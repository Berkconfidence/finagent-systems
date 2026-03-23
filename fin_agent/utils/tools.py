import base64
from typing import List
import os
from langchain_core.tools import tool
from dotenv import load_dotenv
from tavily import TavilyClient

load_dotenv()
tavily_api_key = os.getenv("TAVILY_SEARCH_API")
client = TavilyClient(api_key=tavily_api_key)


def get_pdf_base64(pdf_path: str) -> str:
    """PDF dosyasını okuyup tek bir base64 string'e çevirir."""
    with open(pdf_path, "rb") as f:
        pdf_data = f.read()
    return base64.b64encode(pdf_data).decode("utf-8")

@tool
def search_market_data(company_name: str) -> str:
    """
    Şirketin faaliyet gösterdiği sektördeki riskleri, rakip analizlerini 
    ve güncel haber akışındaki sentiment'i Tavily ile tarar. Sadece veri toplama işlevi görür.
    """

    search_query = f"{company_name} market risks, financial news, competitors, industry outlook"
    
    try:
        tavily_response = client.search(
            query=search_query,
            include_answer="advanced", 
            search_depth="advanced",   
            max_results=5              
        )

        search_context = f"Tavily AI Özeti: {tavily_response.get('answer', '')}\n\nDetaylı Kaynaklar:\n"
        for res in tavily_response.get("results", []):
            search_context += f"- {res.get('title', '')}: {res.get('content', '')}\n"
        
        return search_context
    except Exception as e:
        return f"İnternet araması sırasında hata oluştu veya veri bulunamadı: {str(e)}"
