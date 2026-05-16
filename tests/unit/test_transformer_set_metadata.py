"""Tests for WaybillTransformerSetMetadata."""

from __future__ import annotations

import pytest

from src.transformers import build_transformer
from src.transformers.set_metadata import WaybillTransformerSetMetadata
from src.types.config import ConfigTransformer, TransformerType


@pytest.fixture()
def stream(stream_factory):
    return stream_factory(
        name="Old Name",
        logo_url="https://old.example.com/logo.png",
        tvg_id="old.demo",
    )


class TestWaybillTransformerSetMetadata:
    def test_sets_all_supported_fields(self, stream) -> None:
        t = WaybillTransformerSetMetadata(
            name="New Name",
            logo_url="https://new.example.com/logo.png",
            tvg_id="new.demo",
        )
        result = t.transform(stream)
        assert result is stream
        assert stream.name == "New Name"
        assert stream.logo_url == "https://new.example.com/logo.png"
        assert stream.tvg_id == "new.demo"

    def test_sets_only_provided_fields(self, stream) -> None:
        t = WaybillTransformerSetMetadata(name="Canonical", tvg_id="canon.demo")
        t.transform(stream)
        assert stream.name == "Canonical"
        assert stream.tvg_id == "canon.demo"
        assert stream.logo_url == "https://old.example.com/logo.png"

    def test_raises_when_no_fields_provided(self) -> None:
        with pytest.raises(ValueError, match="setMetadata requires at least one"):
            WaybillTransformerSetMetadata()

    def test_describe_lists_assigned_fields(self) -> None:
        t = WaybillTransformerSetMetadata(name="Canonical", tvg_id="canon.demo")
        assert t.describe() == 'setMetadata -> name="Canonical", tvgId="canon.demo"'

    def test_build_transformer_creates_set_metadata(self, stream) -> None:
        cfg = ConfigTransformer(
            type=TransformerType.SET_METADATA,
            name="Configured Name",
            logo_url="https://configured.example.com/logo.png",
            tvg_id="configured.demo",
        )
        t = build_transformer(cfg)
        assert isinstance(t, WaybillTransformerSetMetadata)
        t.transform(stream)
        assert stream.name == "Configured Name"
        assert stream.logo_url == "https://configured.example.com/logo.png"
        assert stream.tvg_id == "configured.demo"

    def test_renders_template_in_name(self, stream) -> None:
        t = WaybillTransformerSetMetadata(name="{{ brand }} Channel")
        t.transform(stream, variables={"brand": "NBS"})
        assert stream.name == "NBS Channel"

    def test_renders_template_in_tvg_id(self, stream) -> None:
        t = WaybillTransformerSetMetadata(tvg_id="{{ ch_name }}.demo")
        t.transform(stream, variables={"ch_name": "bbc"})
        assert stream.tvg_id == "bbc.demo"

    def test_undefined_template_variable_raises(self, stream) -> None:
        t = WaybillTransformerSetMetadata(name="{{ missing }}")
        with pytest.raises(ValueError, match="Undefined template variable"):
            t.transform(stream, variables={})

    def test_template_field_strings_exposes_fields(self) -> None:
        t = WaybillTransformerSetMetadata(
            name="{{ ch_name }}", tvg_id="{{ ch_name }}.demo"
        )
        pairs = dict(t.template_field_strings())
        assert "{{ ch_name }}" in pairs.values()
        assert "{{ ch_name }}.demo" in pairs.values()
