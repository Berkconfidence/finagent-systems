import os
import base64
from dotenv import load_dotenv
load_dotenv()
from langchain_core.messages import HumanMessage
from langchain_google_vertexai import ChatVertexAI

llm = ChatVertexAI(model="gemini-2.5-flash", temperature=0)

pdf_path = "sample_statement.pdf"
try:
    with open(pdf_path, "rb") as f:
        pdf_b64 = base64.b64encode(f.read()).decode("utf-8")
        
    msg = HumanMessage(content=[
        {"type": "text", "text": "Extract the company name from this PDF."},
        {"type": "file", "base64": pdf_b64, "mime_type": "application/pdf"}
    ])
    res = llm.invoke([msg])
    print(res.content)
except Exception as e:
    print(f"Error: {e}")
