import asyncio
import grpc
from fastapi import FastAPI
from contextlib import asynccontextmanager
import logging
from app.api.router import api_router
from fin_agent.agent import pool
from app.grpc_server import CreditRiskGRPCServer
from fin_proto import credit_score_pb2_grpc

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

logger = logging.getLogger(__name__)

async def serve_grpc():
    """
    gRPC sunucusunu başlatmak için asenkron fonksiyon
    """
    server = grpc.aio.server()
    credit_score_pb2_grpc.add_CreditRiskServiceServicer_to_server(CreditRiskGRPCServer(), server)
    server.add_insecure_port('[::]:50051')
    logger.info("🚀 gRPC Sunucusu 50051 portunda başlatıldı...")
    await server.start()
    await server.wait_for_termination()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI uygulamasının yaşam döngüsü.
    """
    logger.info("FinAgent-360 başlatılıyor... Veritabanı pool'u aktif.")
    grpc_task = asyncio.create_task(serve_grpc())

    yield
    logger.info("FinAgent-360 kapatılıyor... Postgres pool'u temizleniyor.")
    grpc_task.cancel()
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