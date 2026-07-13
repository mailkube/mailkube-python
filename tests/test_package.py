"""Package surface: version, exports, and the py.typed marker."""

from __future__ import annotations

import pathlib

import mailkube


def test_version_is_exposed():
    assert mailkube.__version__ == "0.1.0"


def test_public_symbols_are_exported():
    for name in ("Mailkube", "AsyncMailkube", "verify", "verify_signature", "parse_event", "Email", "MailkubeError"):
        assert hasattr(mailkube, name)
        assert name in mailkube.__all__


def test_py_typed_marker_ships():
    marker = pathlib.Path(mailkube.__file__).parent / "py.typed"
    assert marker.exists()
