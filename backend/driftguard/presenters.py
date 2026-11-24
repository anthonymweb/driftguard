"""Read models: turn stored records into the shapes the console renders.

A target carries its own scannability state and the newest assessment attempt, so the
console never has to infer either from a separate call per row.
"""
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from . import models
from .scanner.engine import scannability_reasons
from .schemas import ScanSummary, TargetRead


def latest_scan_for(db: Session, target_id: int) -> models.Scan | None:
    return db.scalar(
        select(models.Scan)
        .where(models.Scan.target_id == target_id)
        .order_by(models.Scan.id.desc())
        .limit(1)
    )


def latest_scans_for(db: Session, target_ids: list[int]) -> dict[int, models.Scan]:
    if not target_ids:
        return {}
    newest = (
        select(models.Scan.target_id, func.max(models.Scan.id).label("max_id"))
        .where(models.Scan.target_id.in_(target_ids))
        .group_by(models.Scan.target_id)
        .subquery()
    )
    rows = db.scalars(select(models.Scan).join(newest, models.Scan.id == newest.c.max_id))
    return {row.target_id: row for row in rows}


def target_read(target: models.Target, last_scan: models.Scan | None) -> TargetRead:
    reasons = scannability_reasons(target)
    return TargetRead(
        id=target.id,
        name=target.name,
        address=target.address,
        target_type=target.target_type,
        authorization_status=target.authorization_status,
        authorized_by=target.authorized_by,
        authorized_at=target.authorized_at,
        authorization_basis=target.authorization_basis,
        approved_scope=target.approved_scope,
        approved_ports=target.approved_ports,
        discovery_enabled=target.discovery_enabled,
        discovery_wordlist=target.discovery_wordlist,
        status=target.status,
        created_at=target.created_at,
        last_scan=ScanSummary.model_validate(last_scan) if last_scan else None,
        scannable=not reasons,
        refusal_reasons=reasons,
    )
