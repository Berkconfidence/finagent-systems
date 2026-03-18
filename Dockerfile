# Hafif ve performanslı Python imajı
FROM python:3.12-slim

# Çalışma dizini
WORKDIR /app

# Sistem bağımlılıklarını kur (gRPC ve PDF işlemleri için gerekebilir)
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Bağımlılıkları kopyala ve kur
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Tüm proje kodunu kopyala
COPY . .

# gRPC dosyalarını üret (Proto'dan Python koduna)
RUN mkdir -p ./src/services && \
    python -m grpc_tools.protoc -I./proto \
    --python_out=./src/services \
    --grpc_python_out=./src/services \
    ./proto/credit_score.proto
    
# Portları aç
EXPOSE 8000 50051

# Uygulamayı başlat (FastAPI)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]