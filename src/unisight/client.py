from __future__ import annotations

from datetime import datetime
from typing import Any, Iterable, Literal, Mapping

import httpx

from .errors import UniSightAPIError, error_for_status
from .models import (
    Diagnostic,
    DownloadedReport,
    Me,
    Org,
    RawTelemetryPoint,
    ReportJob,
    ReportResult,
    ReportTilesCatalog,
    TrackPoint,
    User,
    UserActive,
    Vehicle,
)

DEFAULT_BASE_URL = "https://api.unisight.ru"
DEFAULT_TIMEOUT = 30.0

Transport = Literal["sync", "async"]


def _iso(value: datetime | str) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def _raise_for_status(resp: httpx.Response) -> None:
    if resp.status_code < 400:
        return
    try:
        body = resp.json()
    except ValueError:
        body = resp.text
    raise error_for_status(resp.status_code, body, dict(resp.headers))


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _build_client(
    *,
    base_url: str,
    token: str,
    timeout: float,
    transport: str,
    proxy: str | None,
    verify: bool,
    **extra: Any,
) -> httpx.BaseClient:
    headers = {"Accept": "application/json", **_auth_headers(token), **extra.pop("headers", {})}
    kwargs: dict[str, Any] = {
        "base_url": base_url.rstrip("/"),
        "timeout": timeout,
        "headers": headers,
        "follow_redirects": True,
    }
    if proxy:
        kwargs["proxy"] = proxy
    if not verify:
        kwargs["verify"] = False
    if transport == "async":
        return httpx.AsyncClient(**kwargs)
    return httpx.Client(**kwargs)


class _Routes:
    @staticmethod
    def me() -> str:
        return "/v1/me"

    @staticmethod
    def orgs() -> str:
        return "/v1/orgs"

    @staticmethod
    def vehicles() -> str:
        return "/v1/vehicles"

    @staticmethod
    def users() -> str:
        return "/v1/users"

    @staticmethod
    def user_active(user_id: int) -> str:
        return f"/v1/users/{user_id}/active"

    @staticmethod
    def user_group(user_id: int) -> str:
        return f"/v1/users/{user_id}/group"

    @staticmethod
    def vehicle(imei: str) -> str:
        return f"/v1/vehicles/{imei}"

    @staticmethod
    def report_tiles() -> str:
        return "/v1/reports/tiles"

    @staticmethod
    def reports() -> str:
        return "/v1/reports"

    @staticmethod
    def report_job(job_id: int) -> str:
        return f"/v1/reports/jobs/{job_id}"

    @staticmethod
    def report_download(job_id: int) -> str:
        return f"/v1/reports/jobs/{job_id}/download"

    @staticmethod
    def diagnostics() -> str:
        return "/v1/diagnostics"

    @staticmethod
    def dispatch() -> str:
        return "/v1/dispatch"

    @staticmethod
    def track(imei: str) -> str:
        return f"/v1/vehicles/{imei}/track"

    @staticmethod
    def raw_telemetry(imei: str) -> str:
        return f"/v1/vehicles/{imei}/telemetry/raw"


class UniSightClient:
    def __init__(
        self,
        token: str,
        *,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT,
        proxy: str | None = None,
        verify: bool = True,
        client: httpx.Client | None = None,
    ) -> None:
        self._client = client or _build_client(
            base_url=base_url,
            token=token,
            timeout=timeout,
            transport="sync",
            proxy=proxy,
            verify=verify,
        )
        self._owns_client = client is None

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> "UniSightClient":
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()

    def _get(self, path: str, *, params: Mapping[str, Any] | None = None) -> Any:
        resp = self._client.get(path, params=params)
        _raise_for_status(resp)
        return resp.json()

    def _post(self, path: str, *, json: Any | None = None, params: Mapping[str, Any] | None = None) -> Any:
        resp = self._client.post(path, json=json, params=params)
        _raise_for_status(resp)
        if resp.status_code == 204 or not resp.content:
            return None
        return resp.json()

    def _patch(self, path: str, *, json: Any | None = None, params: Mapping[str, Any] | None = None) -> Any:
        resp = self._client.patch(path, json=json, params=params)
        _raise_for_status(resp)
        return resp.json() if resp.content else None

    def _delete(self, path: str, *, params: Mapping[str, Any] | None = None) -> None:
        resp = self._client.delete(path, params=params)
        _raise_for_status(resp)

    def _get_bytes(self, path: str, *, params: Mapping[str, Any] | None = None) -> httpx.Response:
        resp = self._client.get(path, params=params)
        _raise_for_status(resp)
        return resp

    def me(self) -> Me:
        data = self._get(_Routes.me())
        return Me.from_dict(data)

    def orgs(self) -> list[Org]:
        data = self._get(_Routes.orgs())
        return [Org.from_dict(o) for o in data]

    def create_org(
        self,
        *,
        name: str,
        admin_login: str,
        admin_password: str,
        timezone: str = "Europe/Moscow",
        role_template: Literal["integrator", "admin"] = "integrator",
        plan_code: str = "start",
        telemetry_retention_days: int | None = None,
        billing_note: str = "",
    ) -> Org:
        body: dict[str, Any] = {
            "name": name,
            "admin_login": admin_login,
            "admin_password": admin_password,
            "timezone": timezone,
            "role_template": role_template,
            "plan_code": plan_code,
            "billing_note": billing_note,
        }
        if telemetry_retention_days is not None:
            body["telemetry_retention_days"] = telemetry_retention_days
        data = self._post(_Routes.orgs(), json=body)
        return Org.from_dict(data)

    def vehicles(self, org_id: int) -> list[Vehicle]:
        data = self._get(_Routes.vehicles(), params={"org_id": org_id})
        return [Vehicle.from_dict(v) for v in data]

    def users(self, org_id: int) -> list[User]:
        data = self._get(_Routes.users(), params={"org_id": org_id})
        return [User.from_dict(u) for u in data]

    def create_vehicle(
        self,
        *,
        org_id: int,
        imei: str,
        label: str = "",
        display_name: str = "",
    ) -> Vehicle:
        data = self._post(
            _Routes.vehicles(),
            json={"imei": imei, "label": label, "display_name": display_name},
            params={"org_id": org_id},
        )
        return Vehicle(
            imei=str(data["imei"]),
            label=str(data.get("label", "")),
            display_name=str(data.get("display_name", "")),
            active=True,
        )

    def create_user(
        self,
        *,
        org_id: int,
        username: str,
        password: str,
        display_name: str = "",
        role_template: Literal["admin", "integrator", "dispatcher", "viewer"] = "viewer",
    ) -> User:
        data = self._post(
            _Routes.users(),
            json={
                "username": username,
                "password": password,
                "display_name": display_name,
                "role_template": role_template,
            },
            params={"org_id": org_id},
        )
        return User.from_dict(data)

    def set_user_active(self, *, org_id: int, user_id: int, active: bool) -> UserActive:
        data = self._patch(_Routes.user_active(user_id), json={"active": active}, params={"org_id": org_id})
        return UserActive.from_dict(data)

    def block_user(self, *, org_id: int, user_id: int) -> UserActive:
        return self.set_user_active(org_id=org_id, user_id=user_id, active=False)

    def set_user_group(
        self,
        *,
        org_id: int,
        user_id: int,
        role_template: Literal["admin", "integrator", "dispatcher", "viewer"],
    ) -> User:
        data = self._patch(
            _Routes.user_group(user_id),
            json={"role_template": role_template},
            params={"org_id": org_id},
        )
        return User.from_dict(data)

    def update_vehicle_name(
        self,
        *,
        org_id: int,
        imei: str,
        label: str | None = None,
        display_name: str | None = None,
    ) -> bool:
        body: dict[str, Any] = {}
        if label is not None:
            body["label"] = label
        if display_name is not None:
            body["display_name"] = display_name
        data = self._patch(_Routes.vehicle(imei), json=body, params={"org_id": org_id})
        return bool(data.get("updated", True)) if isinstance(data, dict) else True

    def delete_vehicle(self, *, org_id: int, imei: str) -> None:
        self._delete(_Routes.vehicle(imei), params={"org_id": org_id})

    def report_tiles(self) -> ReportTilesCatalog:
        data = self._get(_Routes.report_tiles())
        return ReportTilesCatalog.from_dict(data)

    def create_report(
        self,
        *,
        org_id: int,
        imeis: Iterable[str],
        tiles: Iterable[str],
        dt_from: datetime | str,
        dt_to: datetime | str,
        format: Literal["json", "xlsx"] = "json",
        template: str = "custom",
    ) -> ReportResult:
        body = {
            "imeis": list(imeis),
            "tiles": list(tiles),
            "dt_from": _iso(dt_from),
            "dt_to": _iso(dt_to),
            "format": format,
            "template": template,
        }
        data = self._post(_Routes.reports(), json=body, params={"org_id": org_id})
        return ReportResult.from_dict(data)

    def report_job(self, job_id: int) -> ReportJob:
        data = self._get(_Routes.report_job(job_id))
        return ReportJob.from_dict(data)

    def download_report(self, job_id: int) -> DownloadedReport:
        resp = self._get_bytes(_Routes.report_download(job_id))
        cd = resp.headers.get("content-disposition", "")
        filename = job_id
        for part in cd.split(";"):
            part = part.strip()
            if part.startswith("filename="):
                filename = part.split("=", 1)[1].strip('"')
                break
        return DownloadedReport(job_id=job_id, filename=str(filename), content=resp.content)

    def diagnostics(self, org_id: int) -> list[Diagnostic]:
        data = self._get(_Routes.diagnostics(), params={"org_id": org_id})
        return [Diagnostic.from_dict(d) for d in data]

    def dispatch(self, org_id: int) -> dict[str, Any]:
        return self._get(_Routes.dispatch(), params={"org_id": org_id})

    def track(
        self,
        *,
        org_id: int,
        imei: str,
        dt_from: datetime | str,
        dt_to: datetime | str,
    ) -> list[TrackPoint]:
        data = self._get(
            _Routes.track(imei),
            params={
                "org_id": org_id,
                "dt_from": _iso(dt_from),
                "dt_to": _iso(dt_to),
            },
        )
        return [TrackPoint.from_dict(p) for p in data]

    def raw_telemetry(
        self,
        *,
        org_id: int,
        imei: str,
        dt_from: datetime | str,
        dt_to: datetime | str,
        limit: int = 5000,
    ) -> list[RawTelemetryPoint]:
        data = self._get(
            _Routes.raw_telemetry(imei),
            params={
                "org_id": org_id,
                "dt_from": _iso(dt_from),
                "dt_to": _iso(dt_to),
                "limit": limit,
            },
        )
        return [RawTelemetryPoint.from_dict(p) for p in data]

    def health(self) -> dict[str, Any]:
        resp = self._client.get("/")
        _raise_for_status(resp)
        return resp.json()


class AsyncUniSightClient:
    def __init__(
        self,
        token: str,
        *,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT,
        proxy: str | None = None,
        verify: bool = True,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._client = client or _build_client(
            base_url=base_url,
            token=token,
            timeout=timeout,
            transport="async",
            proxy=proxy,
            verify=verify,
        )
        self._owns_client = client is None

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def __aenter__(self) -> "AsyncUniSightClient":
        return self

    async def __aexit__(self, *exc: Any) -> None:
        await self.aclose()

    async def _get(self, path: str, *, params: Mapping[str, Any] | None = None) -> Any:
        resp = await self._client.get(path, params=params)
        _raise_for_status(resp)
        return resp.json()

    async def _post(self, path: str, *, json: Any | None = None, params: Mapping[str, Any] | None = None) -> Any:
        resp = await self._client.post(path, json=json, params=params)
        _raise_for_status(resp)
        if resp.status_code == 204 or not resp.content:
            return None
        return resp.json()

    async def _patch(self, path: str, *, json: Any | None = None, params: Mapping[str, Any] | None = None) -> Any:
        resp = await self._client.patch(path, json=json, params=params)
        _raise_for_status(resp)
        return resp.json() if resp.content else None

    async def _delete(self, path: str, *, params: Mapping[str, Any] | None = None) -> None:
        resp = await self._client.delete(path, params=params)
        _raise_for_status(resp)

    async def _get_bytes(self, path: str, *, params: Mapping[str, Any] | None = None) -> httpx.Response:
        resp = await self._client.get(path, params=params)
        _raise_for_status(resp)
        return resp

    async def me(self) -> Me:
        data = await self._get(_Routes.me())
        return Me.from_dict(data)

    async def orgs(self) -> list[Org]:
        data = await self._get(_Routes.orgs())
        return [Org.from_dict(o) for o in data]

    async def create_org(
        self,
        *,
        name: str,
        admin_login: str,
        admin_password: str,
        timezone: str = "Europe/Moscow",
        role_template: Literal["integrator", "admin"] = "integrator",
        plan_code: str = "start",
        telemetry_retention_days: int | None = None,
        billing_note: str = "",
    ) -> Org:
        body: dict[str, Any] = {
            "name": name,
            "admin_login": admin_login,
            "admin_password": admin_password,
            "timezone": timezone,
            "role_template": role_template,
            "plan_code": plan_code,
            "billing_note": billing_note,
        }
        if telemetry_retention_days is not None:
            body["telemetry_retention_days"] = telemetry_retention_days
        data = await self._post(_Routes.orgs(), json=body)
        return Org.from_dict(data)

    async def vehicles(self, org_id: int) -> list[Vehicle]:
        data = await self._get(_Routes.vehicles(), params={"org_id": org_id})
        return [Vehicle.from_dict(v) for v in data]

    async def users(self, org_id: int) -> list[User]:
        data = await self._get(_Routes.users(), params={"org_id": org_id})
        return [User.from_dict(u) for u in data]

    async def create_vehicle(
        self,
        *,
        org_id: int,
        imei: str,
        label: str = "",
        display_name: str = "",
    ) -> Vehicle:
        data = await self._post(
            _Routes.vehicles(),
            json={"imei": imei, "label": label, "display_name": display_name},
            params={"org_id": org_id},
        )
        return Vehicle(
            imei=str(data["imei"]),
            label=str(data.get("label", "")),
            display_name=str(data.get("display_name", "")),
            active=True,
        )

    async def create_user(
        self,
        *,
        org_id: int,
        username: str,
        password: str,
        display_name: str = "",
        role_template: Literal["admin", "integrator", "dispatcher", "viewer"] = "viewer",
    ) -> User:
        data = await self._post(
            _Routes.users(),
            json={
                "username": username,
                "password": password,
                "display_name": display_name,
                "role_template": role_template,
            },
            params={"org_id": org_id},
        )
        return User.from_dict(data)

    async def set_user_active(self, *, org_id: int, user_id: int, active: bool) -> UserActive:
        data = await self._patch(_Routes.user_active(user_id), json={"active": active}, params={"org_id": org_id})
        return UserActive.from_dict(data)

    async def block_user(self, *, org_id: int, user_id: int) -> UserActive:
        return await self.set_user_active(org_id=org_id, user_id=user_id, active=False)

    async def set_user_group(
        self,
        *,
        org_id: int,
        user_id: int,
        role_template: Literal["admin", "integrator", "dispatcher", "viewer"],
    ) -> User:
        data = await self._patch(
            _Routes.user_group(user_id),
            json={"role_template": role_template},
            params={"org_id": org_id},
        )
        return User.from_dict(data)

    async def update_vehicle_name(
        self,
        *,
        org_id: int,
        imei: str,
        label: str | None = None,
        display_name: str | None = None,
    ) -> bool:
        body: dict[str, Any] = {}
        if label is not None:
            body["label"] = label
        if display_name is not None:
            body["display_name"] = display_name
        data = await self._patch(_Routes.vehicle(imei), json=body, params={"org_id": org_id})
        return bool(data.get("updated", True)) if isinstance(data, dict) else True

    async def delete_vehicle(self, *, org_id: int, imei: str) -> None:
        await self._delete(_Routes.vehicle(imei), params={"org_id": org_id})

    async def report_tiles(self) -> ReportTilesCatalog:
        data = await self._get(_Routes.report_tiles())
        return ReportTilesCatalog.from_dict(data)

    async def create_report(
        self,
        *,
        org_id: int,
        imeis: Iterable[str],
        tiles: Iterable[str],
        dt_from: datetime | str,
        dt_to: datetime | str,
        format: Literal["json", "xlsx"] = "json",
        template: str = "custom",
    ) -> ReportResult:
        body = {
            "imeis": list(imeis),
            "tiles": list(tiles),
            "dt_from": _iso(dt_from),
            "dt_to": _iso(dt_to),
            "format": format,
            "template": template,
        }
        data = await self._post(_Routes.reports(), json=body, params={"org_id": org_id})
        return ReportResult.from_dict(data)

    async def report_job(self, job_id: int) -> ReportJob:
        data = await self._get(_Routes.report_job(job_id))
        return ReportJob.from_dict(data)

    async def download_report(self, job_id: int) -> DownloadedReport:
        resp = await self._get_bytes(_Routes.report_download(job_id))
        cd = resp.headers.get("content-disposition", "")
        filename = job_id
        for part in cd.split(";"):
            part = part.strip()
            if part.startswith("filename="):
                filename = part.split("=", 1)[1].strip('"')
                break
        return DownloadedReport(job_id=job_id, filename=str(filename), content=resp.content)

    async def diagnostics(self, org_id: int) -> list[Diagnostic]:
        data = await self._get(_Routes.diagnostics(), params={"org_id": org_id})
        return [Diagnostic.from_dict(d) for d in data]

    async def dispatch(self, org_id: int) -> dict[str, Any]:
        return await self._get(_Routes.dispatch(), params={"org_id": org_id})

    async def track(
        self,
        *,
        org_id: int,
        imei: str,
        dt_from: datetime | str,
        dt_to: datetime | str,
    ) -> list[TrackPoint]:
        data = await self._get(
            _Routes.track(imei),
            params={
                "org_id": org_id,
                "dt_from": _iso(dt_from),
                "dt_to": _iso(dt_to),
            },
        )
        return [TrackPoint.from_dict(p) for p in data]

    async def raw_telemetry(
        self,
        *,
        org_id: int,
        imei: str,
        dt_from: datetime | str,
        dt_to: datetime | str,
        limit: int = 5000,
    ) -> list[RawTelemetryPoint]:
        data = await self._get(
            _Routes.raw_telemetry(imei),
            params={
                "org_id": org_id,
                "dt_from": _iso(dt_from),
                "dt_to": _iso(dt_to),
                "limit": limit,
            },
        )
        return [RawTelemetryPoint.from_dict(p) for p in data]

    async def health(self) -> dict[str, Any]:
        resp = await self._client.get("/")
        _raise_for_status(resp)
        return resp.json()


__all__ = [
    "DEFAULT_BASE_URL",
    "DEFAULT_TIMEOUT",
    "AsyncUniSightClient",
    "UniSightClient",
    "UniSightAPIError",
]
