from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse

router = APIRouter(tags=["ui"])


@router.get("/")
async def dashboard() -> FileResponse:
    index_path = Path(__file__).resolve().parents[2] / "static" / "index.html"
    return FileResponse(index_path)
