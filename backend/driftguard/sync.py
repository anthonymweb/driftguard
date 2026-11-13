"""Register the lab's targets with the DriftGuard API/database.

Reads the lab's registry (``lab/domain/domain/config.py`` TARGETS) by loading the
lab's domain package from its path, so the backend does not depend on the lab being
installed on ``sys.path``.
"""
from __future__ import annotations

import argparse
import importlib
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import models
from .database import SessionLocal


def _load_lab_domain(repo_root: Path):
    """Import the lab's ``domain`` package from *repo_root* and return it.

    The lab's domain package lives at ``lab/domain`` (``lab/domain/__init__.py``).
    Adding ``lab`` to ``sys.path`` makes ``import domain`` resolve to that package.
    We clear cached ``domain`` modules that do not belong to the lab so the correct
    package is imported, and temporarily prepend the path for the import.
    """
    lab_dir = Path(repo_root) / "lab"
    domain_pkg = lab_dir / "domain"
    lab_str = str(lab_dir)
    pkg_str = str(domain_pkg)
    # Any cached `domain` modules that are not the lab's own are displaced for
    # the duration of the import and put back afterwards, so a long-lived
    # process (the API) does not silently end up with the lab's package
    # installed under the name `domain`.
    displaced: dict[str, Any] = {}
    for name in list(sys.modules):
        if name == "domain" or name.startswith("domain."):
            mod = sys.modules.get(name)
            mod_file = getattr(mod, "__file__", "") or ""
            if pkg_str not in mod_file:
                displaced[name] = mod
                del sys.modules[name]
    inserted = False
    if lab_str not in sys.path:
        sys.path.insert(0, lab_str)
        inserted = True
    try:
        import domain.config as config  # type: ignore
        import domain.state as state  # type: ignore
        # Ensure we have the lab's modules (in case they were previously loaded).
        importlib.reload(config)
        importlib.reload(state)
        return config, state
    finally:
        # Put the lab's modules back the way they were: the caller's process
        # keeps whatever `domain` package it had before.
        for name in list(sys.modules):
            if name == "domain" or name.startswith("domain."):
                mod = sys.modules.get(name)
                mod_file = getattr(mod, "__file__", "") or ""
                if pkg_str in mod_file:
                    del sys.modules[name]
        sys.modules.update(displaced)
        if inserted:
            try:
                sys.path.remove(lab_str)
            except ValueError:
                pass


def load_lab_registry(repo_root: Path | str) -> dict[str, Any]:
    """Return the lab's TARGETS mapping (name -> Target)."""
    config, _state = _load_lab_domain(Path(repo_root))
    return dict(config.TARGETS)


def load_lab_truth(repo_root: Path | str):
    """Return (scan_records, truth_matrix, TARGETS) using the lab's own logic."""
    config, state = _load_lab_domain(Path(repo_root))
    scans = state.read_scans()
    matrix = state.truth_matrix(config.TARGETS, scans)
    return scans, matrix, dict(config.TARGETS)


def target_to_payload(
    target,
    *,
    authorized_by: str,
    authorized_at: datetime,
    authorization_basis: str,
) -> dict[str, Any]:
    """Build the registration payload for a lab Target."""
    return {
        "name": target.name,
        "address": target.base_url,
        "target_type": "web",
        "authorization_status": "authorized",
        "authorized_by": authorized_by,
        "authorized_at": authorized_at,
        "authorization_basis": authorization_basis,
        "approved_scope": list(target.scope),
        "approved_ports": sorted(int(p) for p in target.approved_ports),
        "discovery_enabled": False,
        "discovery_wordlist": None,
        "status": "active",
    }


def _default_authorization():
    return {
        "authorized_by": os.getenv("DRIFTGUARD_SYNC_AUTHORIZED_BY", "local-lab-sync"),
        "authorized_at": datetime.now(timezone.utc),
        "authorization_basis": os.getenv(
            "DRIFTGUARD_SYNC_AUTHORIZATION_BASIS",
            "controlled lab evaluation (eservices-lab)",
        ),
    }


def sync_targets(
    db: Session,
    repo_root: Path | str | None = None,
    *,
    authorized_by: str | None = None,
    authorized_at: datetime | None = None,
    authorization_basis: str | None = None,
) -> int:
    """Register (or update) each lab target in *db*.

    Idempotent: a target matched by name is updated in place rather than duplicated.
    Returns the number of lab targets processed.
    """
    if repo_root is None:
        repo_root = Path(__file__).resolve().parents[2]
    defaults = _default_authorization()
    by = authorized_by or defaults["authorized_by"]
    at = authorized_at or defaults["authorized_at"]
    basis = authorization_basis or defaults["authorization_basis"]
    if at.tzinfo is None:
        at = at.replace(tzinfo=timezone.utc)

    registry = load_lab_registry(repo_root)
    count = 0
    for name, target in registry.items():
        payload = target_to_payload(target, authorized_by=by, authorized_at=at, authorization_basis=basis)
        existing = db.scalar(select(models.Target).where(models.Target.name == name))
        if existing is None:
            db.add(models.Target(**payload))
        else:
            for key, value in payload.items():
                # The authorisation record states *when* the assessment was
                # authorised. Re-syncing must not restamp it: a fresh sync is
                # not a fresh authorisation. It is only replaced when the
                # caller passes an explicit timestamp.
                if key == "authorized_at" and authorized_at is None and existing.authorized_at is not None:
                    continue
                setattr(existing, key, value)
        count += 1
    # The sync is what puts the targets in the registry, so it commits them:
    # a caller (a script, or the API) must not have to remember to.
    db.commit()
    return count


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Sync lab targets into the DriftGuard database.")
    parser.add_argument("--repo-root", default=None, help="Repository root (defaults to this repo).")
    parser.add_argument("--authorized-by", default=None)
    parser.add_argument("--authorization-basis", default=None)
    args = parser.parse_args(argv)
    repo_root = Path(args.repo_root) if args.repo_root else Path(__file__).resolve().parents[2]
    db = SessionLocal()
    try:
        count = sync_targets(
            db,
            repo_root=repo_root,
            authorized_by=args.authorized_by,
            authorization_basis=args.authorization_basis,
        )
        db.commit()
        print(f"Synced {count} targets from lab registry.")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
