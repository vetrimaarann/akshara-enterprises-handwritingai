from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..auth import get_current_admin
from ..database import get_db
from ..models import UploadHistory, User
from ..schemas import AdminStatsOut, UserOut

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/users", response_model=list[UserOut])
def list_all_users(
    _: User = Depends(get_current_admin), db: Session = Depends(get_db)
):
    return db.query(User).all()


@router.get("/stats", response_model=AdminStatsOut)
def get_admin_stats(
    _: User = Depends(get_current_admin), db: Session = Depends(get_db)
):
    total_users = db.query(func.count(User.id)).scalar() or 0
    total_uploads = db.query(func.count(UploadHistory.id)).scalar() or 0
    return {"total_users": total_users, "total_uploads": total_uploads}
