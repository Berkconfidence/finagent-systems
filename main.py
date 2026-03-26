from fastapi import FastAPI
from contextlib import asynccontextmanager
import logging
from app.api.router import api_router
from fin_agent.agent import pool


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI uygulamasının yaşam döngüsü.
    Başlarken: Veritabanı bağlantıları zaten fin_agent/agent.py'de oluşturuldu.
    Kapanırken: Connection pool'u (bağlantı havuzunu) güvenlice kapatır.
    """
    logger.info("FinAgent-360 başlatılıyor... Veritabanı pool'u aktif.")
    yield
    logger.info("FinAgent-360 kapatılıyor... Postgres pool'u temizleniyor.")
    pool.close()

app = FastAPI(
    title="FinAgent-360 API",
    description="Multi-Agent & Multi-Modal Corporate Credit Risk Analysis System",                                                                                  
    version="1.0.0",
    lifespan=lifespan
)

app.include_router(api_router, prefix="/api/v1")

@app.get("/")
async def root():
    return {
        "message": "FinAgent-360 API sistemine hoş geldiniz.",
        "docs_url": "/docs",
        "status": "Running"
    }