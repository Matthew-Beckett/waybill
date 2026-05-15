"""Unit tests for the setMetadata transformer."""

from __future__ import annotations

import sys
import types
from types import SimpleNamespace


# Stub minimal Django module path required by transformer imports.
_channels_models = types.ModuleType("apps.channels.models")
_channels_models.Stream = object  # type: ignore[attr-defined]

_num2words_mod = types.ModuleType("num2words")
_num2words_mod.num2words = lambda *a, **kw: ""  # type: ignore[attr-defined]

_w2n_mod = types.ModuleType("word2number")
_w2n_mod.w2n = SimpleNamespace(word_to_num=lambda s: int(s))  # type: ignore[attr-defined]

for _mod_name, _mod in (
    ("apps", types.ModuleType("apps")),
    ("apps.channels", types.ModuleType("apps.channels")),
    ("apps.channels.models", _channels_models),
    ("num2words", _num2words_mod),
    ("word2number", _w2n_mod),
):
    if _mod_name not in sys.modules:
        sys.modules[_mod_name] = _mod

from src.transformers import build_transformer  # noqa: E402
from src.transformers.set_metadata import WaybillTransformerSetMetadata  # noqa: E402
from src.types.config import ConfigTransformer, TransformerType  # noqa: E402


def _make_stream() -> SimpleNamespace:
    return SimpleNamespace(
        name="Old Name",
        logo_url="https://old.example.com/logo.png",
        tvg_id="old.demo",
    )


class TestSetMetadataTransformer:
    def test_sets_all_supported_fields(self) -> None:
        stream = _make_stream()
        transformer = WaybillTransformerSetMetadata(
            name="New Name",
            logo_url="https://new.example.com/logo.png",
            tvg_id="new.demo",
        )

        result = transformer.transform(stream)

        assert result is stream
        assert stream.name == "New Name"
        assert stream.logo_url == "https://new.example.com/logo.png"
        assert stream.tvg_id == "new.demo"

    def test_sets_only_provided_fields(self) -> None:
        stream = _make_stream()
        transformer = WaybillTransformerSetMetadata(
            name="Canonical", tvg_id="canon.demo"
        )

        transformer.transform(stream)

        assert stream.name == "Canonical"
        assert stream.tvg_id == "canon.demo"
        assert stream.logo_url == "https://old.example.com/logo.png"

    def test_describe_self_includes_assigned_fields(self) -> None:
        transformer = WaybillTransformerSetMetadata(
            name="Canonical", tvg_id="canon.demo"
        )

        assert (
            transformer.describe()
            == 'setMetadata -> name="Canonical", tvgId="canon.demo"'
        )

    def test_raises_when_no_fields_provided(self) -> None:
        try:
            WaybillTransformerSetMetadata()
            assert False, "Expected ValueError"
        except ValueError as exc:
            assert str(exc) == "setMetadata requires at least one metadata field"


class TestSetMetadataBuildTransformer:
    def test_build_transformer_creates_set_metadata(self) -> None:
        cfg = ConfigTransformer(
            type=TransformerType.SET_METADATA,
            name="Configured Name",
            logo_url="https://configured.example.com/logo.png",
            tvg_id="configured.demo",
        )

        transformer = build_transformer(cfg)

        assert isinstance(transformer, WaybillTransformerSetMetadata)
        stream = _make_stream()
        transformer.transform(stream)
        assert stream.name == "Configured Name"
        assert stream.logo_url == "https://configured.example.com/logo.png"
        assert stream.tvg_id == "configured.demo"
