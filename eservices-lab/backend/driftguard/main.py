"""DriftGuard backend foundation: authorized target inventory and evidence history."""
from contextlib import asynccontextmanager
import os

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import models
from .database import Base, engine, get_db
from .schemas import EvidenceRead, ScanRead, TargetCreate, TargetRead


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Initial schema bootstrap. Use Alembic before evolving a deployed database.
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="DriftGuard API", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in os.getenv(
        "DRIFTGUARD_UI_ORIGINS",
        "http://127.0.0.1:5173,http://localhost:5173,http://127.0.0.1:4173",
    ).split(",") if origin.strip()],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)


@app.get("/health")
def health():
    return {"status": "ok", "service": "driftguard-api"}


@app.post("/api/targets", response_model=TargetRead, status_code=status.HTTP_201_CREATED)
def register_target(payload: TargetCreate, db: Session = Depends(get_db)):
    target = models.Target(**payload.model_dump())
    db.add(target)
    db.commit()
    db.refresh(target)
    return target


@app.get("/api/targets", response_model=list[TargetRead])
def list_targets(db: Session = Depends(get_db)):
    return list(db.scalars(select(models.Target).order_by(models.Target.id.desc())))


@app.get("/api/targets/{target_id}", response_model=TargetRead)
def get_target(target_id: int, db: Session = Depends(get_db)):
    target = db.get(models.Target, target_id)
    if target is None:
        raise HTTPException(status_code=404, detail="Target not found")
    return target


@app.post("/api/targets/{target_id}/scans", response_model=ScanRead, status_code=status.HTTP_201_CREATED)
def record_scan_request(target_id: int, db: Session = Depends(get_db)):
    """Create an auditable scan request only for an active, explicitly authorized target.

    Assessment execution is intentionally a separate next milestone; this endpoint records
    the authorization gate and does not claim that a network assessment has run.
    """
    target = db.get(models.Target, target_id)
    if target is None:
        raise HTTPException(status_code=404, detail="Target not found")
    if target.status != "active" or target.authorization_status != "authorized":
        raise HTTPException(status_code=403, detail="Target must be active and explicitly authorized")
    if not target.approved_scope:
        raise HTTPException(status_code=422, detail="Target has no approved assessment scope")
    scan = models.Scan(target_id=target.id, status="queued")
    db.add(scan)
    db.commit()
    db.refresh(scan)
    return scan


@app.get("/api/targets/{target_id}/scans", response_model=list[ScanRead])
def list_scans(target_id: int, db: Session = Depends(get_db)):
    if db.get(models.Target, target_id) is None:
        raise HTTPException(status_code=404, detail="Target not found")
    return list(db.scalars(select(models.Scan).where(models.Scan.target_id == target_id).order_by(models.Scan.id.desc())))


@app.get("/api/scans/{scan_id}/evidence", response_model=list[EvidenceRead])
def list_evidence(scan_id: int, db: Session = Depends(get_db)):
    if db.get(models.Scan, scan_id) is None:
        raise HTTPException(status_code=404, detail="Scan not found")
    return list(db.scalars(select(models.Evidence).where(models.Evidence.scan_id == scan_id).order_by(models.Evidence.id)))
