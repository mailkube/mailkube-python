"""Library logging: silent by default, opt-in only.

Following the standard-library guidance for libraries, the package attaches a
``NullHandler`` and never configures handlers or levels itself — the host application
owns that. Logging is turned on explicitly via :func:`enable_logging` or the
``MAILKUBE_LOG`` environment variable.
"""

from __future__ import annotations

import logging
import os
from collections.abc import Mapping

logger = logging.getLogger("mailkube")
logger.addHandler(logging.NullHandler())

_SENSITIVE_HEADERS = frozenset({"authorization", "idempotency-key"})


def get_logger(name: str) -> logging.Logger:
    """Return a child logger under the ``mailkube`` namespace.

    Args:
        name: The module name (pass ``__name__``).

    Returns:
        A ``logging.Logger`` that inherits the package's ``NullHandler``.
    """
    return logging.getLogger(name)


def enable_logging(level: int | str = "DEBUG") -> None:
    """Attach a ``StreamHandler`` to the ``mailkube`` logger.

    This is opt-in: the SDK never calls it for you (except when the ``MAILKUBE_LOG``
    environment variable is set). Call it from your application to see SDK debug output.

    Args:
        level: The log level to set on the ``mailkube`` logger.
    """
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s %(name)s %(levelname)s %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(level)


def redact_headers(headers: Mapping[str, str]) -> dict[str, str]:
    """Return a copy of ``headers`` with sensitive values masked, safe for logging.

    Args:
        headers: The headers to redact.

    Returns:
        A new dict where secret headers (Authorization, Idempotency-Key) are ``"***"``.
    """
    return {key: ("***" if key.lower() in _SENSITIVE_HEADERS else value) for key, value in headers.items()}


_ENV_LEVEL = os.environ.get("MAILKUBE_LOG")
if _ENV_LEVEL:
    enable_logging(_ENV_LEVEL.upper())
