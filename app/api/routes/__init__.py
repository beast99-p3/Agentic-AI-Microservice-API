from fastapi import APIRouter

from app.api.routes.agent import router as agent_router
from app.api.routes.health import router as health_router
from app.api.routes.prompt import router as prompt_router
from app.api.routes.tools import router as tools_router
from app.api.routes.ui import router as ui_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(tools_router)
api_router.include_router(agent_router)
api_router.include_router(prompt_router)
api_router.include_router(ui_router)
