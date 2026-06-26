from __future__ import annotations

from typing import Any


class UniSightError(Exception):
    pass


class UniSightAPIError(UniSightError):
    def __init__(
        self,
        message: str,
        *,
        status_code: int,
        code: str | None = None,
        request_id: str | None = None,
        body: Any = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.request_id = request_id
        self.body = body

    def __str__(self) -> str:
        parts = [super().__str__()]
        if self.code:
            parts.append(f"code={self.code}")
        if self.status_code:
            parts.append(f"status={self.status_code}")
        if self.request_id:
            parts.append(f"request_id={self.request_id}")
        return ", ".join(parts)


class UnauthorizedError(UniSightAPIError):
    pass


class ForbiddenError(UniSightAPIError):
    pass


class NotFoundError(UniSightAPIError):
    pass


class ValidationError(UniSightAPIError):
    pass


class RateLimitError(UniSightAPIError):
    def __init__(self, *args: Any, retry_after: int | None = None, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.retry_after = retry_after


class ConflictError(UniSightAPIError):
    pass


_STATUS_TO_ERROR: dict[int, type[UniSightAPIError]] = {
    401: UnauthorizedError,
    403: ForbiddenError,
    404: NotFoundError,
    409: ConflictError,
    422: ValidationError,
    429: RateLimitError,
}


def error_for_status(status_code: int, body: Any, headers: dict[str, str]) -> UniSightAPIError:
    message = "ошибка API"
    code: str | None = None
    request_id = headers.get("x-request-id")
    if isinstance(body, dict) and isinstance(body.get("error"), dict):
        err = body["error"]
        message = str(err.get("message") or message)
        code = err.get("code")
        request_id = err.get("request_id") or request_id
    elif isinstance(body, dict) and body.get("detail"):
        message = str(body["detail"])
    elif isinstance(body, str) and body:
        message = body

    cls = _STATUS_TO_ERROR.get(status_code, UniSightAPIError)
    if cls is RateLimitError:
        retry = headers.get("retry-after")
        return RateLimitError(
            message,
            status_code=status_code,
            code=code,
            request_id=request_id,
            body=body,
            retry_after=int(retry) if retry and retry.isdigit() else None,
        )
    return cls(message, status_code=status_code, code=code, request_id=request_id, body=body)
