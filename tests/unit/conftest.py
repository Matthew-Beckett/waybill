"""Shared fixtures and module stubs for the unit test suite.

Stubs for Django's ORM and vendored number-conversion libraries are installed
once here so that individual test modules do not need to replicate the
boilerplate.  Each stub is registered into ``sys.modules`` only when the key
is absent, making this safe to import multiple times.
"""

from __future__ import annotations

import pathlib
import sys
import types
from types import SimpleNamespace

import pytest


VENDOR_PATH = str(pathlib.Path(__file__).resolve().parents[2] / "src" / "vendor")


def _install_stubs() -> None:
    """Register minimal in-process stubs for external dependencies."""
    channels_models = types.ModuleType("apps.channels.models")
    channels_models.Stream = object  # type: ignore[attr-defined]

    stubs: list[tuple[str, types.ModuleType]] = [
        ("apps", types.ModuleType("apps")),
        ("apps.channels", types.ModuleType("apps.channels")),
        ("apps.channels.models", channels_models),
    ]

    num2words_mod = types.ModuleType("num2words")
    num2words_mod.num2words = lambda *a, **kw: ""  # type: ignore[attr-defined]

    w2n_mod = types.ModuleType("word2number")
    w2n_mod.w2n = SimpleNamespace(word_to_num=lambda s: int(s))  # type: ignore[attr-defined]

    stubs += [
        ("num2words", num2words_mod),
        ("word2number", w2n_mod),
    ]

    for name, mod in stubs:
        if name not in sys.modules:
            sys.modules[name] = mod


_install_stubs()


@pytest.fixture()
def stream_factory():
    """Return a factory that builds lightweight stream-like namespaces."""

    def _make(
        name: str = "NBS One",
        tvg_id: str = "bbc.one",
        logo_url: str = "",
        **extra: str,
    ) -> SimpleNamespace:
        return SimpleNamespace(name=name, tvg_id=tvg_id, logo_url=logo_url, **extra)

    return _make


@pytest.fixture()
def real_number_libs(monkeypatch: pytest.MonkeyPatch) -> None:
    """Swap the number-conversion stubs for the real vendored libraries.

    Apply to any test class or function that exercises the actual
    num2words / word2number behaviour.
    """
    monkeypatch.syspath_prepend(VENDOR_PATH)

    for key in list(sys.modules):
        if key == "num2words" or key.startswith("num2words."):
            monkeypatch.delitem(sys.modules, key)
        if key == "word2number" or key.startswith("word2number."):
            monkeypatch.delitem(sys.modules, key)

    import num2words as _real_n2w  # noqa: PLC0415
    from word2number import w2n as _real_w2n  # noqa: PLC0415

    import src.transformers.convert_cardinal_numbers as _ccn  # noqa: PLC0415

    monkeypatch.setattr(_ccn, "num2words", _real_n2w.num2words)
    monkeypatch.setattr(_ccn, "w2n", _real_w2n)
