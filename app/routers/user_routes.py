from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..database import get_db
from ..models import UploadHistory, User
from ..ocr import (
    extract_handwritten_text_with_meta,
)
from ..schemas import OCRExtractResponse, UploadHistoryOut

router = APIRouter(tags=["User"])
UPLOAD_DIR = Path("uploads")


@router.get("/dashboard")
def get_dashboard(current_user: User = Depends(get_current_user)):
    return {
        "message": f"Welcome to your dashboard, {current_user.full_name}",
        "user": {
            "id": current_user.id,
            "full_name": current_user.full_name,
            "email": current_user.email,
            "role": current_user.role,
        },
    }


@router.post("/uploads/extract", response_model=OCRExtractResponse)
async def extract_upload_text(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Validate MIME type
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only image uploads are supported.",
        )
    
    # Read file content once
    content = await file.read()
    
    # Save to disk first
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    extension = Path(file.filename or "upload.png").suffix or ".png"
    file_name = f"{uuid4().hex}{extension}"
    file_path = UPLOAD_DIR / file_name
    
    with open(file_path, "wb") as output_file:
        output_file.write(content)
    
    # Run OCR with the content bytes directly
    try:
        await file.seek(0)
        extracted_text, confidence_score, engine_used, analysis = await extract_handwritten_text_with_meta(file)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"OCR processing failed: {str(e)}",
        )

    # Save to database
    upload_record = UploadHistory(
        user_id=current_user.id,
        image_path=str(file_path),
        extracted_text=extracted_text,
    )
    db.add(upload_record)
    db.commit()

    return {
        "image_path": str(file_path),
        "extracted_text": extracted_text,
        "confidence_score": confidence_score,
        "engine_used": engine_used,
        "analysis": analysis,
    }


@router.get("/uploads/history", response_model=list[UploadHistoryOut])
def get_upload_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return (
        db.query(UploadHistory)
        .filter(UploadHistory.user_id == current_user.id)
        .order_by(UploadHistory.timestamp.desc())
        .all()
    )
