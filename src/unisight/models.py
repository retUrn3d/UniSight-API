from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Org:
    id: int
    name: str
    timezone: str
    active: bool

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Org":
        return cls(
            id=int(d["id"]),
            name=str(d.get("name", "")),
            timezone=str(d.get("timezone", "")),
            active=bool(d.get("active", True)),
        )


@dataclass
class TokenInfo:
    id: int
    label: str
    owner_type: str
    owner_id: int
    scopes: list[str]
    created_at: str
    last_used_at: str | None


@dataclass
class Me:
    token: TokenInfo
    orgs: list[Org]

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Me":
        t = d.get("token") or {}
        return cls(
            token=TokenInfo(
                id=int(t.get("id", 0)),
                label=str(t.get("label", "")),
                owner_type=str(t.get("owner_type", "")),
                owner_id=int(t.get("owner_id", 0)),
                scopes=list(t.get("scopes", [])),
                created_at=str(t.get("created_at", "")),
                last_used_at=t.get("last_used_at"),
            ),
            orgs=[Org.from_dict(o) for o in d.get("orgs", [])],
        )


@dataclass
class Vehicle:
    imei: str
    label: str
    display_name: str
    active: bool = True

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Vehicle":
        return cls(
            imei=str(d["imei"]),
            label=str(d.get("label", "")),
            display_name=str(d.get("display_name", "")),
            active=bool(d.get("active", True)),
        )


@dataclass
class User:
    id: int
    user_id: int
    username: str
    display_name: str
    role_template: str
    org_id: int
    active: bool

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "User":
        user_id = int(d.get("user_id", d["id"]))
        return cls(
            id=int(d.get("id", user_id)),
            user_id=user_id,
            username=str(d.get("username", "")),
            display_name=str(d.get("display_name", "")),
            role_template=str(d.get("role_template", "")),
            org_id=int(d.get("org_id", 0)),
            active=bool(d.get("active", True)),
        )


@dataclass
class UserActive:
    id: int
    user_id: int
    org_id: int
    active: bool

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "UserActive":
        user_id = int(d.get("user_id", d["id"]))
        return cls(
            id=int(d.get("id", user_id)),
            user_id=user_id,
            org_id=int(d["org_id"]),
            active=bool(d["active"]),
        )


@dataclass
class ReportTile:
    key: str
    label: str


@dataclass
class ReportTemplate:
    key: str
    label: str
    tiles: list[str]


@dataclass
class ReportTilesCatalog:
    tiles: list[ReportTile]
    templates: list[ReportTemplate]

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "ReportTilesCatalog":
        return cls(
            tiles=[ReportTile(key=str(t["key"]), label=str(t.get("label", ""))) for t in d.get("tiles", [])],
            templates=[
                ReportTemplate(
                    key=str(t["key"]),
                    label=str(t.get("label", "")),
                    tiles=list(t.get("tiles", [])),
                )
                for t in d.get("templates", [])
            ],
        )


@dataclass
class ReportResult:
    job_id: int
    status: str
    rows: list[dict[str, Any]] = field(default_factory=list)
    count: int = 0
    download_url: str | None = None

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "ReportResult":
        return cls(
            job_id=int(d.get("job_id", 0)),
            status=str(d.get("status", "")),
            rows=list(d.get("rows", [])),
            count=int(d.get("count", 0)),
            download_url=d.get("download_url"),
        )


@dataclass
class ReportJob:
    id: int
    org_id: int
    status: str
    file_path: str | None = None
    error_message: str | None = None
    created_at: str | None = None
    finished_at: str | None = None

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "ReportJob":
        return cls(
            id=int(d.get("id", 0)),
            org_id=int(d.get("org_id", 0)),
            status=str(d.get("status", "")),
            file_path=d.get("file_path"),
            error_message=d.get("error_message"),
            created_at=d.get("created_at"),
            finished_at=d.get("finished_at"),
        )


@dataclass
class Finding:
    data: dict[str, Any]


@dataclass
class Diagnostic:
    imei: str
    health_score: int
    crit_count: int
    warn_count: int
    findings: list[dict[str, Any]]

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Diagnostic":
        return cls(
            imei=str(d.get("imei", "")),
            health_score=int(d.get("health_score", 100)),
            crit_count=int(d.get("crit_count", 0)),
            warn_count=int(d.get("warn_count", 0)),
            findings=list(d.get("findings", [])),
        )


@dataclass
class TrackPoint:
    device_time: str
    lat: float
    lon: float
    speed: float | int | None = None
    received_at: str | None = None

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "TrackPoint":
        return cls(
            device_time=str(d.get("device_time", "")),
            lat=float(d["lat"]) if d.get("lat") is not None else 0.0,
            lon=float(d["lon"]) if d.get("lon") is not None else 0.0,
            speed=d.get("speed"),
            received_at=d.get("received_at"),
        )


@dataclass
class RawTelemetryPoint:
    device_time: str
    received_at: str | None = None
    lat: float | None = None
    lon: float | None = None
    speed: float | int | None = None
    adc: Any = None
    iobits: Any = None
    params: Any = None

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "RawTelemetryPoint":
        return cls(
            device_time=str(d.get("device_time", "")),
            received_at=d.get("received_at"),
            lat=d.get("lat"),
            lon=d.get("lon"),
            speed=d.get("speed"),
            adc=d.get("adc"),
            iobits=d.get("iobits"),
            params=d.get("params"),
        )


@dataclass
class DownloadedReport:
    job_id: int
    filename: str
    content: bytes
