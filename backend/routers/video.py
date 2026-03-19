from fastapi import APIRouter

router = APIRouter()


@router.get("/", summary="Video endpoint stub")
async def video_index():
    return {"status": "ok", "router": "video"}
