from fastapi import APIRouter, UploadFile, File, HTTPException
from backend.services.transcription import transcription_service
import shutil
import os

router = APIRouter()


@router.post("/transcribe")
async def transcribe_video(file: UploadFile = File(...)):
    temp_path = f"temp_{file.filename}"
    try:
        with open(temp_path, "wb") as f:
            shutil.copyfileobj(file.file, f)
        result = transcription_service.transcribe(temp_path)
        return {"transcription": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)
