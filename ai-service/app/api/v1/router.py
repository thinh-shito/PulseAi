from fastapi import APIRouter
from app.api.v1.endpoints import health, workflow, chat

router = APIRouter(prefix="/api/v1")

router.include_router(health.router, tags=["health"])
router.include_router(workflow.router, tags=["workflow"])
router.include_router(chat.router, tags=["chat"])