from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from . import models
from .sync import load_lab_truth
from evaluate import evaluate, load_engine_evidence, planted_from_registry


def _duplicate_completed_labels(db: Session) -> list[str]:
    rows = db.execute(
        select(models.Scan.label, func.count())
        .where(models.Scan.label.is_not(None), models.Scan.status == "completed")
        .group_by(models.Scan.label)
        .having(func.count() > 1)
    ).all()
    return sorted(label for label, _ in rows)


def build_evaluation_report(db: Session, repo_root: Path) -> dict:
    try:
        scans, truth_matrix, targets = load_lab_truth(repo_root)
    except Exception as exc:  # missing or unreadable lab ground truth
        return {"available": False, "reason": str(exc)}
    scan_labels = [scan.label for scan in scans if scan.label]
    duplicates = sorted({label for label in scan_labels if scan_labels.count(label) > 1})
    duplicates += _duplicate_completed_labels(db)
    duplicates = sorted(set(duplicates))
    if duplicates:
        return {"available": False,
                "reason": "duplicate scan labels make the ground-truth join ambiguous",
                "duplicates": duplicates}
    evidence_by_label, _ = load_engine_evidence(db)
    report = evaluate(truth_matrix, evidence_by_label, scan_labels,
                      planted_from_registry(targets))
    return {"available": True, "generated_at": datetime.now(timezone.utc).isoformat(), **report}