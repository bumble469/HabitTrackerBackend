from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.models import User
from app.schemas import ExportOut, ImportIn, ImportOut
from app.services import transfer_service

router = APIRouter(prefix="/api", tags=["data"])


@router.get("/export", response_model=ExportOut)
def export_data(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return transfer_service.export_user_data(db, user)


@router.post("/import", response_model=ImportOut, status_code=201)
def import_data(body: ImportIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return transfer_service.import_user_data(db, user, body)


