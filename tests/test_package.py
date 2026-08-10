"""Package surface: version, exports, and the py.typed marker."""

from __future__ import annotations

import importlib.metadata
import pathlib

import mailkube


def test_version_matches_the_installed_distribution():
    """The reported version must be the released one, not a literal that can drift from it."""
    assert mailkube.__version__ == importlib.metadata.version("mailkube")
    assert mailkube.__version__ != "0.0.0", "the distribution metadata was not found"


def test_user_agent_carries_the_real_version():
    client = mailkube.Mailkube(api_key="mk_test")

    assert client._default_headers()["User-Agent"] == f"mailkube-python/{mailkube.__version__}"


def test_public_symbols_are_exported():
    exported = (
        "Mailkube",
        "AsyncMailkube",
        "verify",
        "verify_signature",
        "parse_event",
        "Email",
        "MailkubeError",
        "ErrorName",
        "ScheduledEmail",
        "ScheduledEmailPage",
        "ScheduledEmailListParams",
        "ScheduledEmailUpdateParams",
        "ScheduledEmailBatchUpdateParams",
        "ScheduledEmailBatchCancel",
        "ScheduledEmailBatchUpdate",
        "CanceledScheduledEmail",
        "Pagination",
        "PageSteps",
    )
    for name in exported:
        assert hasattr(mailkube, name)
        assert name in mailkube.__all__


def test_py_typed_marker_ships():
    marker = pathlib.Path(mailkube.__file__).parent / "py.typed"
    assert marker.exists()
