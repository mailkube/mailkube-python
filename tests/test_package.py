"""Package surface: version, exports, and the py.typed marker."""

from __future__ import annotations

import importlib.metadata
import pathlib

import pytest

import mailkube


def test_version_matches_the_installed_distribution():
    """The reported version must be the released one, not a literal that can drift from it."""
    assert mailkube.__version__ == importlib.metadata.version("mailkube")
    assert mailkube.__version__ != "0.0.0", "the distribution metadata was not found"


def test_user_agent_carries_the_real_version():
    client = mailkube.Mailkube(api_key="mk_test")

    assert client._default_headers()["User-Agent"] == f"mailkube-python/{mailkube.__version__}"


def test_the_user_agent_version_segment_starts_with_a_digit():
    """The contract is `mailkube-<lang>/<version>` — a `v` prefix from the git tag would violate it.

    Deliberately NOT written as `== f"mailkube-python/{__version__}"`: that form is tautological
    and would happily pass on `mailkube-python/v1.0.0`. Asserting the shape is what catches a
    version resolved from the raw tag instead of from PEP 440 distribution metadata.
    """
    user_agent = mailkube.Mailkube(api_key="mk_test")._default_headers()["User-Agent"]
    prefix, slash, version_segment = user_agent.partition("/")

    assert (prefix, slash) == ("mailkube-python", "/")
    assert version_segment[:1].isdigit(), f"stray non-numeric version prefix in {user_agent!r}"


def test_user_agent_suffix_follows_the_sdk_token():
    """A wrapping tool gets attribution without hiding which SDK made the call."""
    client = mailkube.Mailkube(api_key="mk_test", user_agent_suffix="my-cli/1.0.0")
    agent = client._default_headers()["User-Agent"]

    assert agent == f"mailkube-python/{mailkube.__version__} my-cli/1.0.0"


def test_the_async_client_carries_the_user_agent_suffix_too():
    """The option is on both flavours, or an async caller is silently unattributed."""
    client = mailkube.AsyncMailkube(api_key="mk_test", user_agent_suffix="my-cli/1.0.0")

    assert client._default_headers()["User-Agent"] == f"mailkube-python/{mailkube.__version__} my-cli/1.0.0"


@pytest.mark.parametrize("suffix", ["", "   ", "cli/1.0\ninjected: yes", "cli/1.0\rinjected: yes"])
def test_an_unusable_user_agent_suffix_leaves_the_header_untouched(suffix: str):
    """Blank is a no-op; CR/LF is dropped rather than cleaned, so nothing can split the header."""
    client = mailkube.Mailkube(api_key="mk_test", user_agent_suffix=suffix)

    assert client._default_headers()["User-Agent"] == f"mailkube-python/{mailkube.__version__}"


def test_a_surrounding_space_in_the_user_agent_suffix_is_trimmed():
    client = mailkube.Mailkube(api_key="mk_test", user_agent_suffix="  my-cli/1.0.0  ")

    assert client._default_headers()["User-Agent"].endswith(" my-cli/1.0.0")


def test_public_symbols_are_exported():
    exported = (
        "Mailkube",
        "AsyncMailkube",
        "verify",
        "verify_signature",
        "sign",
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
