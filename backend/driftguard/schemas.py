"""Validated API contracts."""
from datetime import datetime
from typing import Literal
from urllib.parse import urlsplit
import ipaddress
import re

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class TargetCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    address: str = Field(min_length=1, max_length=500)
    target_type: Literal["web", "api", "host"]
    authorization_status: Literal["pending", "authorized"] = "pending"
    authorized_by: str | None = Field(default=None, min_length=1, max_length=200)
    authorized_at: datetime | None = None
    authorization_basis: str | None = Field(default=None, min_length=1, max_length=500)
    approved_scope: list[Literal["tls", "network", "http_api"]] = Field(default_factory=list)
    approved_ports: list[int] = Field(default_factory=list)
    discovery_enabled: bool = False
    discovery_wordlist: str | None = Field(default=None, max_length=1000)
    status: Literal["active", "inactive"] = "active"

    @field_validator("address")
    @classmethod
    def trim_address(cls, value: str) -> str:
        value = value.strip()
        if not value or any(c in value for c in "\r\n\t"):
            raise ValueError("address must be a single hostname or URL")
        parsed = urlsplit(value if "://" in value else f"//{value}")
        if parsed.scheme and parsed.scheme not in {"http", "https"}:
            raise ValueError("only HTTP or HTTPS URLs are supported")
        if not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError("address must not contain credentials, query, or fragment data")
        if parsed.path not in {"", "/"}:
            raise ValueError("register a hostname or origin URL without a path")
        try:
            port = parsed.port
        except ValueError as exc:
            raise ValueError("address contains an invalid port") from exc
        if port is not None and not 1 <= port <= 65535:
            raise ValueError("address port must be between 1 and 65535")
        hostname = parsed.hostname.rstrip(".")
        try:
            ipaddress.ip_address(hostname)
        except ValueError:
            if len(hostname) > 253 or not re.fullmatch(r"(?i)(?=.{1,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)(?:\.(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?))*", hostname):
                raise ValueError("address must contain a valid hostname or IP address")
        return value

    @field_validator("approved_ports")
    @classmethod
    def valid_ports(cls, ports: list[int]) -> list[int]:
        if any(port < 1 or port > 65535 for port in ports):
            raise ValueError("approved ports must be between 1 and 65535")
        return sorted(set(ports))

    @model_validator(mode="after")
    def require_authorization_record(self):
        if self.authorization_status == "authorized":
            missing = [
                name
                for name, value in (
                    ("authorized_by", self.authorized_by),
                    ("authorized_at", self.authorized_at),
                    ("authorization_basis", self.authorization_basis),
                )
                if value is None or (isinstance(value, str) and not value.strip())
            ]
            if missing:
                raise ValueError(
                    "authorized targets must record who authorised the assessment, when, and on what basis: "
                    + ", ".join(missing)
                )
        return self


class ScanSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    status: str
    started_at: datetime
    completed_at: datetime | None


class TargetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    address: str
    target_type: str
    authorization_status: str
    authorized_by: str | None
    authorized_at: datetime | None
    authorization_basis: str | None
    approved_scope: list[str]
    approved_ports: list[int]
    discovery_enabled: bool
    discovery_wordlist: str | None
    status: str
    created_at: datetime
    last_scan: ScanSummary | None = None
    scannable: bool = False
    refusal_reasons: list[str] = Field(default_factory=list)


class ScanRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    target_id: int
    label: str | None = None
    status: str
    started_at: datetime
    completed_at: datetime | None
    is_baseline: bool
    error: str | None = None


class EvidenceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    scan_id: int
    fingerprint: str
    category: str
    title: str
    severity: str
    resource: str
    details: dict
    observed_at: datetime


class TokenRequest(BaseModel):
    username: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=1, max_length=200)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    role: str
    username: str


class UserCreate(BaseModel):
    username: str = Field(min_length=1, max_length=80, pattern=r"^[A-Za-z0-9._-]+$")
    # Hashed at rest; the minimum keeps a token worth issuing in the first place.
    password: str = Field(min_length=8, max_length=200)
    role: Literal["viewer", "operator", "admin"]


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    username: str
    role: str
    created_at: datetime


class DriftEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    scan_id: int
    evidence_fingerprint: str
    classification: str
    recorded_at: datetime


class FingerprintMeta(BaseModel):
    title: str
    category: str
    severity: str
    resource: str


class DriftCounts(BaseModel):
    NEW: int = 0
    PERSISTENT: int = 0
    FIXED: int = 0
    RECURRING: int = 0


class DriftSummary(BaseModel):
    state: Literal["BASELINE", "NO DRIFT", "CHANGED", "INCOMPLETE"]
    counts: DriftCounts = Field(default_factory=DriftCounts)


class HistoryScan(BaseModel):
    scan: ScanRead
    comparable: bool
    evidence: list[EvidenceRead] = Field(default_factory=list)
    drift: list[DriftEventRead] = Field(default_factory=list)
    summary: DriftSummary


class TargetHistory(BaseModel):
    target: TargetRead
    scans: list[HistoryScan] = Field(default_factory=list)
    fingerprints: dict[str, FingerprintMeta] = Field(default_factory=dict)


class StatsRead(BaseModel):
    targets: int
    scans: int
    evidence: int
    drift_events: int
    auth_mode: str
    redaction: dict


class EvaluationRead(BaseModel):
    available: bool
    reason: str | None = None
    duplicates: list[str] = Field(default_factory=list)
    generated_at: datetime | None = None
    overall: dict | None = None
    per_area: dict | None = None
    per_target: dict | None = None
    unmeasured: dict | None = None
    scan_labels: list[str] | None = None
