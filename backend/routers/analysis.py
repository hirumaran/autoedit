from fastapi import APIRouter

router = APIRouter()


@router.get("/", summary="Analysis endpoint stub")
async def analysis_index():
    return {"status": "ok", "router": "analysis"}
