"""Relational records. Scan evidence is append-only; later scans never replace it."""
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def utcnow():
    return datetime.now(timezone.utc)


class Target(Base):
    __tablename__ = "targets"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    address: Mapped[str] = mapped_column(String(500), nullable=False)
    target_type: Mapped[str] = mapped_column(String(30), nullable=False)
    authorization_status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    approved_scope: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    approved_ports: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    scans: Mapped[list["Scan"]] = relationship(back_populates="target", cascade="all, delete-orphan")


class Scan(Base):
    __tablename__ = "scans"
    __table_args__ = (Index("ix_scans_target_started", "target_id", "started_at"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    target_id: Mapped[int] = mapped_column(ForeignKey("targets.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="completed")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_baseline: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    target: Mapped[Target] = relationship(back_populates="scans")
    evidence: Mapped[list["Evidence"]] = relationship(back_populates="scan", cascade="all, delete-orphan")


class Evidence(Base):
    __tablename__ = "scan_evidence"
    __table_args__ = (UniqueConstraint("scan_id", "fingerprint", name="uq_evidence_scan_fingerprint"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    scan_id: Mapped[int] = mapped_column(ForeignKey("scans.id", ondelete="CASCADE"), nullable=False, index=True)
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(30), nullable=False)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    resource: Mapped[str] = mapped_column(String(500), nullable=False)
    details: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    scan: Mapped[Scan] = relationship(back_populates="evidence")


class DriftEvent(Base):
    __tablename__ = "drift_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    target_id: Mapped[int] = mapped_column(ForeignKey("targets.id", ondelete="CASCADE"), nullable=False, index=True)
    scan_id: Mapped[int] = mapped_column(ForeignKey("scans.id", ondelete="CASCADE"), nullable=False, index=True)
    evidence_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    classification: Mapped[str] = mapped_column(String(20), nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)


class Remediation(Base):
    __tablename__ = "remediations"

    id: Mapped[int] = mapped_column(primary_key=True)
    target_id: Mapped[int] = mapped_column(ForeignKey("targets.id", ondelete="CASCADE"), nullable=False, index=True)
    evidence_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    reported_by: Mapped[str] = mapped_column(String(120), nullable=False)
    note: Mapped[str] = mapped_column(Text, nullable=False)
    reported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    verification_scan_id: Mapped[int | None] = mapped_column(ForeignKey("scans.id", ondelete="SET NULL"))
    verification_outcome: Mapped[str | None] = mapped_column(String(20))
