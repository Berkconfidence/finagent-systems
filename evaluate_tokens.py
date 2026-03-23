import sys
import base64
if "langchain_google_vertexai" not in sys.modules:
    try:
        from langchain_google_vertexai import ChatVertexAI
    except Exception:
        pass

import time
print("Checking PDF size...")
with open("sample_statement.pdf", "rb") as f:
    pdf_b64 = base64.b64encode(f.read()).decode("utf-8")
print(f"Base64 string length: {len(pdf_b64)} characters")
