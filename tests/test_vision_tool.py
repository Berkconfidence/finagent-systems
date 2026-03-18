import sys
import os

# Proje kök dizinini Python yoluna ekle (Import hatalarını önlemek için)
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from fin_agent.utils.tools import analyze_financial_statement

def run_test():
    # Kök dizindeki PDF'i hedef gösteriyoruz
    pdf_path = "./sample_statement.pdf" 
    
    print(f"--- {pdf_path} Analiz Ediliyor ---")
    try:
        result = analyze_financial_statement(pdf_path)
        print("Analiz Başarılı!")
        print(result)
    except Exception as e:
        print(f"Bir hata oluştu: {e}")

if __name__ == "__main__":
    run_test()