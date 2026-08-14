"""The package version, read from the installed distribution metadata.

There is deliberately **no literal** here, and none anywhere else in the tree.
semantic-release creates the git tag, ``hatch-vcs`` resolves that tag into the
distribution metadata at build time, and this module reads it back — so the runtime version
equals the released version by construction rather than by discipline.

A second, hand-maintained constant is precisely how a package ends up reporting a version
it is not: this module pinned ``0.1.0`` while releases went out as ``1.0.0`` through
``1.2.0``, so every request's ``User-Agent`` misattributed the client and made SDK
adoption unreadable in server-side telemetry.
"""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("mailkube")
except PackageNotFoundError:  # pragma: no cover — only when imported from an uninstalled source tree
    __version__ = "0.0.0"
