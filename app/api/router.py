from fastapi import APIRouter

from app.api.endpoints import analysis, history

api_router = APIRouter()

api_router.include_router(
    analysis.router, 
    prefix="/analysis", 
    tags=["Kredi Analizi (Analysis Süreçleri)"]
)

api_router.include_router(
    history.router,
    prefix="/history",
    tags=["Şirket Geçmişi (Long-Term Memory)"]
)
