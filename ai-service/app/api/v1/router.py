from fastapi import APIRouter
from app.api.v1.endpoints import (
    health,
    chat,
    document,
)

router = APIRouter(prefix="/api/v1")

router.include_router(health.router, tags=["health"])
router.include_router(chat.router, tags=["chat"])
router.include_router(document.router, tags=["document"])
