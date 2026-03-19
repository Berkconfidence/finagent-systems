import fitz
import base64
from typing import List, Dict, Any
from google.cloud import aiplatform
from vertexai.generative_models import GenerativeModel, Part, Image
import json
import os
from dotenv import load_dotenv
from tavily import TavilyClient

load_dotenv()
tavily_api_key = os.getenv("TAVILY_SEARCH_API")
client = TavilyClient(api_key=tavily_api_key)

model = GenerativeModel("gemini-2.5-flash")

def pdf_to_images(pdf_path: str) -> List[str]:
    """PDF dosyasını her sayfası bir base64 görsel olacak şekilde listeye çevirir."""
    doc = fitz.open(pdf_path)
    images_base64 = []
    
    for page in doc:
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
        img_bytes = pix.tobytes("png")
        images_base64.append(base64.b64encode(img_bytes).decode("utf-8"))
    
    return images_base64

from langchain_core.tools import tool

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

    