"""DriftGuard backend foundation: authorized target inventory and evidence history."""
from contextlib import asynccontextmanager
import os
import time

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Query, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import func, select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from . import models, presenters
from .audit import audit
from .auth import (
    Principal,
    auth_enabled,
    current_principal,
    hash_password,
    issue_token,
    optional_principal,
    require_role,
    validate_auth_config,
    verify_password,
)
from .database import Base, engine, get_db, get_session_factory
from .logconfig import configure_logging
from .redaction import redact_evidence_payload
from .scanner.engine import ScanRefused, ensure_scannable, run_scan_in_background
from .schemas import (
    DriftCounts,
    DriftSummary,
    EvidenceRead,
    FingerprintMeta,
    HistoryScan,
    ScanRead,
    StatsRead,
    TargetCreate,
    TargetHistory,
    TargetRead,
    TokenRequest,
    TokenResponse,
    UserCreate,
    UserRead,
)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Initial schema bootstrap. Use Alembic before evolving a deployed database.
    validate_auth_config()
    Base.metadata.create_all(bind=engine)
    configure_logging()
    yield


app = FastAPI(title="DriftGuard API", version="0.1.0", lifespan=lifespan)

# Politeness: assessment requests are bounded per client. The limit is read from
# the environment on every request so an operator can tune it without a restart.
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
def rate_limit_exceeded(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """429 carrying a ``Retry-After`` hint.

    slowapi's built-in handler only emits that hint when header injection is
    enabled, and enabling it makes the library's wrapper reject any endpoint that
    returns a model instead of a ``Response`` (it looks for a Flask-style
    ``response`` argument). The hint is therefore derived here from the window
    that was hit.
    """
    headers: dict[str, str] = {}
    current = getattr(request.state, "view_rate_limit", None)
    if current:
        item, args = current
        # ``slowapi.Limiter`` exposes the underlying strategy as ``.limiter``.
        reset_at, _remaining = limiter.limiter.get_window_stats(item, *args)
        headers["Retry-After"] = str(max(1, int(reset_at - time.time()) + 1))
    return JSONResponse(
        {"detail": "Rate limit exceeded: retry later"},
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        headers=headers,
    )


def scan_rate_limit() -> str:
    """The per-client rate limit for queueing assessments, e.g. ``10/minute``."""
    return os.getenv("DRIFTGUARD_SCAN_RATE_LIMIT", "10/minute")


def login_rate_limit() -> str:
    """The per-client rate limit for credential attempts, e.g. ``20/minute``."""
    return os.getenv("DRIFTGUARD_LOGIN_RATE_LIMIT", "20/minute")


app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in os.getenv(
        "DRIFTGUARD_UI_ORIGINS",
        "http://127.0.0.1:5173,http://localhost:5173,http://127.0.0.1:4173",
    ).split(",") if origin.strip()],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)


@app.get("/health")
def health():
    """Liveness: the process is up and answering."""
    return {"status": "ok", "service": "driftguard-api"}


@app.get("/ready")
def ready(db: Session = Depends(get_db)):
    """Readiness: the process is up *and* the database answers.

    An orchestrator uses ``/health`` to decide whether to restart the process and
    ``/ready`` to decide whether to send it traffic; conflating the two would let
    a service with an unreachable database keep accepting work it cannot record.
    """
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "not_ready", "database": "unavailable"},
        )
    return {"status": "ready", "database": "ok", "service": "driftguard-api"}


@app.post("/api/auth/token", response_model=TokenResponse)
@limiter.limit(login_rate_limit)
def login(payload: TokenRequest, request: Request, db: Session = Depends(get_db)):
    """Exchange credentials for a bearer token.

    Credential attempts are rate limited per client so a guessing attack is
    bounded; refusals are audited because a failed login against an assessment
    service is itself an attributable event.
    """
    user = db.scalar(select(models.User).where(models.User.username == payload.username))
    if user is None or not verify_password(payload.password, user.password_hash):
        audit("auth.login_refused", username=payload.username, reason="invalid credentials")
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token, expires_in = issue_token(Principal(user.username, user.role))
    audit("auth.login", actor=user.username, role=user.role)
    return TokenResponse(
        access_token=token,
        expires_in=expires_in,
        role=user.role,
        username=user.username,
    )


@app.post("/api/users", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(payload: UserCreate, request: Request, db: Session = Depends(get_db)):
    """Create an API user.

    The very first user bootstraps the installation without a token — otherwise
    a fresh deployment could never be locked down. Once any user exists, only an
    admin may create further accounts.
    """
    count = db.scalar(select(func.count()).select_from(models.User)) or 0
    if count == 0:
        principal = optional_principal(request)
        actor = principal.username if principal else "bootstrap"
    else:
        principal = current_principal(request)  # 401 when no usable credential
        if not principal.has("admin"):
            raise HTTPException(
                status_code=403,
                detail=f"role '{principal.role}' may not create users; 'admin' required",
            )
        actor = principal.username
    existing = db.scalar(select(models.User).where(models.User.username == payload.username))
    if existing is not None:
        raise HTTPException(status_code=409, detail="Username already exists")
    user = models.User(
        username=payload.username,
        password_hash=hash_password(payload.password),
        role=payload.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    audit("user.created", actor=actor, username=user.username, role=user.role)
    return user


@app.post("/api/targets", response_model=TargetRead, status_code=status.HTTP_201_CREATED)
def register_target(payload: TargetCreate, db: Session = Depends(get_db),
                    principal: Principal = Depends(require_role("admin"))):
    target = models.Target(**payload.model_dump())
    db.add(target)
    db.commit()
    db.refresh(target)
    audit(
        "target.registered",
        actor=target.authorized_by,
        target_id=target.id,
        name=target.name,
        authorization_status=target.authorization_status,
        basis=target.authorization_basis,
        registered_by=principal.username,
    )
    return presenters.target_read(target, None)


@app.get("/api/targets", response_model=list[TargetRead])
def list_targets(db: Session = Depends(get_db),
                 principal: Principal = Depends(require_role("viewer"))):
    targets = list(db.scalars(select(models.Target).order_by(models.Target.id.desc())))
    scans = presenters.latest_scans_for(db, [target.id for target in targets])
    return [presenters.target_read(target, scans.get(target.id)) for target in targets]


@app.get("/api/targets/{target_id}", response_model=TargetRead)
def get_target(target_id: int, db: Session = Depends(get_db),
               principal: Principal = Depends(require_role("viewer"))):
    target = db.get(models.Target, target_id)
    if target is None:
        raise HTTPException(status_code=404, detail="Target not found")
    return presenters.target_read(target, presenters.latest_scan_for(db, target.id))


@app.get("/api/targets/{target_id}/history", response_model=TargetHistory)
def target_history(target_id: int, limit: int = Query(20, ge=1, le=100),
                   db: Session = Depends(get_db),
                   principal: Principal = Depends(require_role("viewer"))):
    target = db.get(models.Target, target_id)
    if target is None:
        raise HTTPException(status_code=404, detail="Target not found")
    scans = list(db.scalars(
        select(models.Scan).where(models.Scan.target_id == target_id)
        .order_by(models.Scan.id.desc()).limit(limit)))
    scan_ids = [scan.id for scan in scans]
    evidence_by_scan = {scan_id: [] for scan_id in scan_ids}
    drift_by_scan = {scan_id: [] for scan_id in scan_ids}
    if scan_ids:
        for row in db.scalars(select(models.Evidence).where(models.Evidence.scan_id.in_(scan_ids)).order_by(models.Evidence.id)):
            evidence_by_scan[row.scan_id].append(row)
        for row in db.scalars(select(models.DriftEvent).where(models.DriftEvent.scan_id.in_(scan_ids)).order_by(models.DriftEvent.id)):
            drift_by_scan[row.scan_id].append(row)
    earliest_completed_id = db.scalar(
        select(func.min(models.Scan.id)).where(
            models.Scan.target_id == target_id, models.Scan.status == "completed"
        )
    )
    history_scans = []
    for scan in scans:
        comparable = scan.status == "completed"
        drift_rows = drift_by_scan[scan.id] if comparable else []
        counts = {"NEW": 0, "PERSISTENT": 0, "FIXED": 0, "RECURRING": 0}
        for row in drift_rows:
            if row.classification in counts:
                counts[row.classification] += 1
        if not comparable:
            state = "INCOMPLETE"
        elif scan.is_baseline or scan.id == earliest_completed_id:
            state = "BASELINE"
        elif not drift_rows:
            state = "NO DRIFT"
        else:
            state = "CHANGED"
        history_scans.append(HistoryScan(
            scan=scan,
            comparable=comparable,
            evidence=evidence_by_scan[scan.id],
            drift=drift_rows,
            summary=DriftSummary(state=state, counts=DriftCounts(**counts)),
        ))

    referenced = {ev.fingerprint for rows in evidence_by_scan.values() for ev in rows}
    referenced |= {row.evidence_fingerprint for rows in drift_by_scan.values() for row in rows}
    catalogue: dict[str, FingerprintMeta] = {}
    if referenced:
        for ev in db.scalars(
            select(models.Evidence).where(models.Evidence.fingerprint.in_(referenced))
            .order_by(models.Evidence.id.desc())
        ):
            if ev.fingerprint not in catalogue:
                catalogue[ev.fingerprint] = FingerprintMeta(
                    title=ev.title, category=ev.category,
                    severity=ev.severity, resource=ev.resource,
                )

    return TargetHistory(
        target=presenters.target_read(target, presenters.latest_scan_for(db, target_id)),
        scans=history_scans,
        fingerprints=catalogue,
    )


@app.get("/api/stats", response_model=StatsRead)
def stats(db: Session = Depends(get_db),
          principal: Principal = Depends(require_role("viewer"))):
    counts = {}
    for name, model in (("targets", models.Target), ("scans", models.Scan),
                        ("evidence", models.Evidence), ("drift_events", models.DriftEvent)):
        counts[name] = db.scalar(select(func.count()).select_from(model)) or 0
    return StatsRead(
        **counts,
        auth_mode="jwt" if auth_enabled() else "local_research",
        redaction={"enabled": True, "token_map": "local-only"},
    )


@app.post("/api/targets/{target_id}/scans", response_model=ScanRead, status_code=status.HTTP_201_CREATED)
@limiter.limit(scan_rate_limit)
def record_scan_request(target_id: int, background: BackgroundTasks, request: Request,
                        label: str | None = None,
                        db: Session = Depends(get_db), session_factory=Depends(get_session_factory),
                        principal: Principal = Depends(require_role("operator"))):
    """Run an assessment for an active, explicitly authorised target with approved scope.

    The scan is queued and the assessment runs in the background; the scan's status moves
    from queued to completed, completed_with_errors, or failed as the assessment proceeds.
    A target that is not scannable is refused with an explicit reason and no scan is run.
    An optional ground-truth scan label (for example ``?label=S3``) can be stored so the
    scan can be joined to the lab's recorded observations.
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
        audit("scan.refused", actor=principal.username, target_id=target_id, reason=reason, http_status=code)
        raise HTTPException(status_code=code, detail=f"Scan refused: {reason}")
    scan = models.Scan(target_id=target.id, status="queued", label=label)
    db.add(scan)
    db.commit()
    db.refresh(scan)
    audit("scan.requested", actor=principal.username, target_id=target.id, scan_id=scan.id, label=label)
    background.add_task(run_scan_in_background, scan.id, session_factory)
    return scan


@app.get("/api/targets/{target_id}/scans", response_model=list[ScanRead])
def list_scans(target_id: int, db: Session = Depends(get_db),
               principal: Principal = Depends(require_role("viewer"))):
    if db.get(models.Target, target_id) is None:
        raise HTTPException(status_code=404, detail="Target not found")
    return list(db.scalars(select(models.Scan).where(models.Scan.target_id == target_id).order_by(models.Scan.id.desc())))


@app.get("/api/scans/{scan_id}/evidence", response_model=list[EvidenceRead])
def list_evidence(scan_id: int, db: Session = Depends(get_db),
                  principal: Principal = Depends(require_role("viewer"))):
    if db.get(models.Scan, scan_id) is None:
        raise HTTPException(status_code=404, detail="Scan not found")
    return list(db.scalars(select(models.Evidence).where(models.Evidence.scan_id == scan_id).order_by(models.Evidence.id)))


@app.get("/api/scans/{scan_id}/evidence/redacted", response_model=list[EvidenceRead])
def list_evidence_redacted(scan_id: int, db: Session = Depends(get_db),
                           principal: Principal = Depends(require_role("viewer"))):
    """Shareable view: evidence with sensitive values tokenised.

    This is the redacted/raw boundary — the form that may be shared or sent to an
    AI. The token map is kept local-only and is never returned.
    """
    if db.get(models.Scan, scan_id) is None:
        raise HTTPException(status_code=404, detail="Scan not found")
    rows = list(db.scalars(select(models.Evidence).where(models.Evidence.scan_id == scan_id).order_by(models.Evidence.id)))
    redacted = []
    for ev in rows:
        payload = {
            "id": ev.id,
            "scan_id": ev.scan_id,
            "fingerprint": ev.fingerprint,
            "category": ev.category,
            "title": ev.title,
            "severity": ev.severity,
            "resource": ev.resource,
            "details": ev.details,
            "observed_at": ev.observed_at,
        }
        redacted.append(redact_evidence_payload(payload))
    audit("evidence.exported", actor=principal.username, scan_id=scan_id, redacted=True, count=len(redacted))
    return redacted
