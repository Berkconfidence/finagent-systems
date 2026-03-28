# Hafif ve performanslı Python imajı
FROM python:3.12-slim

# Çalışma dizini
WORKDIR /app

# Sistem bağımlılıklarını kur
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Bağımlılıkları kopyala ve kur
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Tüm proje kodunu kopyala
COPY . .

# gRPC dosyalarını üret
RUN python -m grpc_tools.protoc -I./fin_proto \
    --python_out=./fin_proto \
    --grpc_python_out=./fin_proto \
    ./fin_proto/credit_score.proto
    
# Portları aç
EXPOSE 8000 50051

# Uygulamayı başlat (FastAPI)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]