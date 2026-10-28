"""Conservative bounded read transport; no retries unless explicitly selected."""

from __future__ import annotations

import errno
import hashlib
import socket
import ssl
import time
from datetime import UTC, datetime
from http.client import IncompleteRead
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, build_opener

TRANSIENT_NETWORK_ERRNOS = {
    errno.EAGAIN,
    errno.ECONNABORTED,
    errno.ECONNREFUSED,
    errno.ECONNRESET,
    errno.EHOSTUNREACH,
    errno.ENETDOWN,
    errno.ENETUNREACH,
    errno.ETIMEDOUT,
}
TRANSIENT_HTTP_STATUSES = {408, 425, 429, 500, 502, 503, 504}
MAX_RAW_BYTES = 16_000_000
MAX_READ_ATTEMPTS = 4


def is_retryable_request_error(error, transient_http_statuses):
    if isinstance(error, HTTPError):
        return error.code in transient_http_statuses
    reason = error.reason if isinstance(error, URLError) else error
    if isinstance(reason, ssl.SSLError):
        return False
    if isinstance(reason, (TimeoutError, ConnectionError)):
        return True
    if isinstance(reason, socket.gaierror):
        return reason.errno == socket.EAI_AGAIN
    return isinstance(reason, OSError) and reason.errno in TRANSIENT_NETWORK_ERRNOS


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def guarded_urlopen(request, timeout=45):
    """Never follow a provider redirect, including one to another origin."""
    return build_opener(_NoRedirect()).open(request, timeout=timeout)


def validate_attempts(max_attempts):
    if type(max_attempts) is not int or not 1 <= max_attempts <= MAX_READ_ATTEMPTS:
        raise ValueError("Explicit read-attempt budget must be an integer from 1 to 4")


def _origin(url):
    parsed = urlsplit(url)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.port not in (None, 443)
        or parsed.fragment
    ):
        raise ValueError("Exact HTTPS request origin required")
    return parsed.scheme, parsed.hostname, parsed.port or 443


def read_response(
    request,
    request_attempts,
    *,
    retain,
    opener=None,
    max_attempts=1,
    sleep=None,
    allow_404=False,
):
    """Persist available response bytes before status/JSON interpretation.

    The retention callback runs outside the network-error catch. Storage and
    interpretation failures are never retried. Bodies beyond the byte cap are
    retained as a diagnostic prefix and rejected, never marked complete.
    """
    validate_attempts(max_attempts)
    expected_origin = _origin(request.full_url)
    if request.get_method() != "GET":
        raise ValueError("Read-only GET required")
    opener = opener or guarded_urlopen
    sleep = sleep or time.sleep
    digest = hashlib.sha256(request.full_url.encode()).hexdigest()
    for attempt in range(1, max_attempts + 1):
        error = None
        raw = None
        status = None
        date = None
        final_url = request.full_url
        try:
            with opener(request, timeout=45) as response:
                status = response.status
                date = response.headers.get("Date")
                if hasattr(response, "geturl"):
                    final_url = response.geturl()
                raw = response.read(MAX_RAW_BYTES + 1)
        except HTTPError as caught:
            error = caught
            status = caught.code
            date = caught.headers.get("Date") if caught.headers else None
            final_url = caught.geturl()
            try:
                raw = caught.read(MAX_RAW_BYTES + 1)
            except (URLError, OSError, TimeoutError, IncompleteRead) as body_error:
                raw = getattr(body_error, "partial", None)
                error = body_error
            finally:
                caught.close()
        except (URLError, OSError, TimeoutError, IncompleteRead) as caught:
            error = caught
            if isinstance(getattr(caught, "partial", None), bytes):
                raw = caught.partial
        if raw is not None:
            if not isinstance(raw, bytes):
                raise ValueError("Transport returned non-byte content")
            retain(raw, status, date, attempt)
        if _origin(final_url) != expected_origin:
            raise ValueError("Response origin differs from requested origin")
        if raw is not None and len(raw) > MAX_RAW_BYTES:
            raise ValueError(
                "Response beyond bounded raw-byte limit; diagnostic prefix retained"
            )
        if type(status) is not int and raw is not None:
            raise ValueError("Exact integer HTTP status required")
        if error is None:
            if status != 200:
                raise ValueError("Unexpected successful response status")
            return raw, status, date, attempt
        if isinstance(error, HTTPError) and status == 404 and allow_404:
            return raw, status, date, attempt
        retryable = is_retryable_request_error(error, TRANSIENT_HTTP_STATUSES)
        reason = error.reason if isinstance(error, URLError) else error
        request_attempts.append(
            {
                "request_sha256": digest,
                "attempt": attempt,
                "observed_at_utc": datetime.now(UTC).isoformat(),
                "error_type": type(error).__name__,
                "http_status": status,
                "network_error_type": type(reason).__name__,
                "network_errno": getattr(reason, "errno", None),
                "retryable": retryable,
                "available_response_bytes": len(raw) if raw is not None else None,
            }
        )
        if not retryable or attempt == max_attempts:
            raise error
        sleep(min(60, 10 * (2 ** (attempt - 1))))
    raise AssertionError("Bounded read loop ended unexpectedly")
