"""DriftGuard backend foundation: authorized target inventory and evidence history."""
from contextlib import asynccontextmanager
import os

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import models
from .database import Base, engine, get_db, get_session_factory
from .scanner.engine import ScanRefused, ensure_scannable, run_scan_in_background
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
def record_scan_request(target_id: int, background: BackgroundTasks, db: Session = Depends(get_db),
                        session_factory=Depends(get_session_factory)):
    """Run an assessment for an active, explicitly authorised target with approved scope.

    The scan is queued and the assessment runs in the background; the scan's status moves
    from queued to completed, completed_with_errors, or failed as the assessment proceeds.
    A target that is not scannable is refused with an explicit reason and no scan is run.
    """
    target = db.get(models.Target, target_id)
    if target is None:
        raise HTTPException(status_code=404, detail="Target not found")
    try:
        ensure_scannable(target)
    except ScanRefused as exc:
        reason = str(exc)
        if "must be active" in reason or "must be explicitly authorized" in reason:
            code = 403
        else:
            code = 422
        raise HTTPException(status_code=code, detail=f"Scan refused: {reason}")
    scan = models.Scan(target_id=target.id, status="queued")
    db.add(scan)
    db.commit()
    db.refresh(scan)
    background.add_task(run_scan_in_background, scan.id, session_factory)
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
