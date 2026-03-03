from fastapi import FastAPI
from fastapi import Depends, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from pathlib import Path
from uuid import uuid4

from . import models
from .auth import get_current_user
from .database import engine, get_db
from .models import UploadHistory, User
from .ocr import extract_handwritten_text
from .routers import admin_routes, auth_routes, user_routes
from .schemas import UploadHistoryOut

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="HandwriteAI API")
UPLOAD_DIR = Path("uploads")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_routes.router)
app.include_router(user_routes.router)
app.include_router(admin_routes.router)


@app.get("/")
def root():
    return FileResponse("index.html")


@app.get("/health")
def health_check():
    return {"message": "HandwriteAI API is running"}


@app.post("/upload")
async def upload_image(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    extracted_text, _ = await extract_handwritten_text(file)

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    extension = Path(file.filename or "upload.png").suffix or ".png"
    file_name = f"{uuid4().hex}{extension}"
    file_path = UPLOAD_DIR / file_name

    content = await file.read()
    await file.seek(0)
    with open(file_path, "wb") as output_file:
        output_file.write(content)

    upload_record = UploadHistory(
        user_id=current_user.id,
        image_path=str(file_path),
        extracted_text=extracted_text,
    )
    db.add(upload_record)
    db.commit()

    return {"extracted_text": extracted_text}


@app.get("/history", response_model=list[UploadHistoryOut])
def get_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return (
        db.query(UploadHistory)
        .filter(UploadHistory.user_id == current_user.id)
        .order_by(UploadHistory.timestamp.desc())
        .all()
    )
