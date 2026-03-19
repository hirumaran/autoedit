from fastapi import APIRouter

router = APIRouter()


@router.get("/", summary="Export endpoint stub")
async def export_index():
    return {"status": "ok", "router": "export"}
