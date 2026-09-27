"""Typed errors shared by the data sources and the user interface.

The UI has to tell apart "the source answered something we cannot use" from
"the source answered, and the answer is legitimately empty": only the first
case is worth an error message. Every network-facing module therefore raises
:class:`DataSourceError` with a machine-readable ``reason`` instead of
returning an empty result or a hardcoded substitute.
"""

from __future__ import annotations

#: The source answered, but not with a success status.
REASON_HTTP_STATUS = "http_status"

#: The source could not be reached at all (timeout, DNS, TLS, refused).
REASON_NETWORK_ERROR = "network_error"

#: The page was read, but it no longer carries the token or field we need.
REASON_TOKEN_NOT_FOUND = "token_not_found"

#: The body arrived but could not be parsed into the expected structure.
REASON_MALFORMED_RESPONSE = "malformed_response"


class DataSourceError(RuntimeError):
    """A remote source could not be used, with the reason carried separately.

    Parameters
    ----------
    source:
        Human-readable name of the source, e.g. ``"MPC What's Observable"``.
    reason:
        Machine-readable cause, one of the ``REASON_*`` constants of this
        module; the UI maps it to a translated label.
    detail:
        Optional extra context for logs (HTTP status, exception text, ...).
    """

    def __init__(self, source: str, reason: str, detail: str = "") -> None:
        self.source = source
        self.reason = reason
        self.detail = detail
        message = f"{source}: {reason}"
        if detail:
            message = f"{message} ({detail})"
        super().__init__(message)
