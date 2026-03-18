import fitz  # PyMuPDF
import base64
from typing import List, Dict, Any
from google.cloud import aiplatform
from vertexai.generative_models import GenerativeModel, Part, Image
import json

# 1. PDF Sayfalarını Görsele Çeviren Fonksiyon
def pdf_to_images(pdf_path: str) -> List[str]:
    """PDF dosyasını her sayfası bir base64 görsel olacak şekilde listeye çevirir."""
    doc = fitz.open(pdf_path)
    images_base64 = []
    
    for page in doc:
        # Yüksek kalite için 300 DPI (zoom=4)
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
        img_bytes = pix.tobytes("png")
        images_base64.append(base64.b64encode(img_bytes).decode("utf-8"))
    
    return images_base64

# 2. Gemini 2.0 Vision Analiz Aracı
def analyze_financial_statement(pdf_path: str) -> Dict[str, Any]:
    """
    Gemini 2.0 Vision kullanarak mizan/bilanço analizi yapar.
    """
    images = pdf_to_images(pdf_path)
    # Gemini 2.0 Flash modeli (Hızlı ve etkili)
    model = GenerativeModel("gemini-2.5-flash")
    
    # Prompt: Modelin rasyonel ve yapılandırılmış çıktı vermesini zorluyoruz
    prompt = """
    Aşağıdaki finansal tablo görüntüsünü analiz et ve şu bilgileri JSON formatında çıkar:
    - Şirket Adı
    - Toplam Varlıklar (Total Assets)
    - Net Borç (Net Debt)
    - FAVÖK (EBITDA)
    - Cari Oran (Current Ratio)
    
    Yalnızca saf JSON çıktısı ver, açıklama yapma.
    """
    
    # Sadece ilk sayfayı test amaçlı gönderiyoruz
    image_part = Part.from_data(data=base64.b64decode(images[0]), mime_type="image/png")
    
    response = model.generate_content([prompt, image_part])
    
    # JSON temizleme ve parse etme
    try:
        cleaned_response = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(cleaned_response)
    except Exception as e:
        return {"error": f"Parse hatası: {str(e)}", "raw": response.text}

# 3. Piyasa Haberleri Tool (Mock örneği)
def get_market_news(company_name: str) -> str:
    """Şirket hakkındaki son haberleri simüle eder (İleride Tavily/Google Search olacak)."""
    return f"{company_name} sektörü için 2025 büyüme beklentileri pozitif yönde."