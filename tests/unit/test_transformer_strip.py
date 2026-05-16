"""Tests for WaybillTransformerStrip."""

from __future__ import annotations

import pytest

from src.transformers.strip import WaybillTransformerStrip


class TestWaybillTransformerStrip:
    def test_strips_prefix(self, stream_factory) -> None:
        t = WaybillTransformerStrip(prefix="UK: ")
        s = stream_factory(name="UK: BBC One")
        t.transform(s)
        assert s.name == "BBC One"

    def test_strips_suffix(self, stream_factory) -> None:
        t = WaybillTransformerStrip(suffix=" HD")
        s = stream_factory(name="BBC One HD")
        t.transform(s)
        assert s.name == "BBC One"

    def test_strips_both_prefix_and_suffix(self, stream_factory) -> None:
        t = WaybillTransformerStrip(prefix="[", suffix="]")
        s = stream_factory(name="[BBC One]")
        t.transform(s)
        assert s.name == "BBC One"

    def test_prefix_not_present_leaves_name_unchanged(self, stream_factory) -> None:
        t = WaybillTransformerStrip(prefix="UK: ")
        s = stream_factory(name="BBC One")
        t.transform(s)
        assert s.name == "BBC One"

    def test_suffix_not_present_leaves_name_unchanged(self, stream_factory) -> None:
        t = WaybillTransformerStrip(suffix=" HD")
        s = stream_factory(name="BBC One SD")
        t.transform(s)
        assert s.name == "BBC One SD"

    def test_partial_match_does_not_strip(self, stream_factory) -> None:
        t = WaybillTransformerStrip(prefix="UK: ")
        s = stream_factory(name="UK BBC One")
        t.transform(s)
        assert s.name == "UK BBC One"

    def test_returns_stream_instance(self, stream_factory) -> None:
        t = WaybillTransformerStrip(prefix="UK: ")
        s = stream_factory(name="UK: BBC One")
        assert t.transform(s) is s

    def test_operates_on_tvg_id_field(self, stream_factory) -> None:
        t = WaybillTransformerStrip(suffix=".demo", field="tvg_id")
        s = stream_factory(tvg_id="bbc.demo")
        t.transform(s)
        assert s.tvg_id == "bbc"

    def test_empty_prefix_and_suffix_is_no_op(self, stream_factory) -> None:
        t = WaybillTransformerStrip()
        s = stream_factory(name="BBC One")
        t.transform(s)
        assert s.name == "BBC One"

    def test_strips_prefix_only_once(self, stream_factory) -> None:
        t = WaybillTransformerStrip(prefix="UK: ")
        s = stream_factory(name="UK: UK: BBC")
        t.transform(s)
        assert s.name == "UK: BBC"

    def test_describe_shows_prefix(self) -> None:
        t = WaybillTransformerStrip(prefix="UK: ")
        assert "UK: " in t.describe()
        assert "prefix" in t.describe()

    def test_describe_shows_suffix(self) -> None:
        t = WaybillTransformerStrip(suffix=" HD")
        assert "HD" in t.describe()
        assert "suffix" in t.describe()

    def test_describe_shows_field_when_not_name(self) -> None:
        t = WaybillTransformerStrip(suffix=".demo", field="tvg_id")
        assert "tvg_id" in t.describe()

    def test_renders_template_in_prefix(self, stream_factory) -> None:
        t = WaybillTransformerStrip(prefix="{{ provider }}| ")
        s = stream_factory(name="UK| BBC One")
        t.transform(s, variables={"provider": "UK"})
        assert s.name == "BBC One"

    def test_renders_template_in_suffix(self, stream_factory) -> None:
        t = WaybillTransformerStrip(suffix=" {{ quality }}")
        s = stream_factory(name="BBC One HD")
        t.transform(s, variables={"quality": "HD"})
        assert s.name == "BBC One"

    def test_undefined_template_variable_in_prefix_raises(self, stream_factory) -> None:
        t = WaybillTransformerStrip(prefix="{{ missing }}| ")
        s = stream_factory(name="UK| BBC One")
        with pytest.raises(ValueError, match="Undefined template variable"):
            t.transform(s, variables={})

    def test_template_field_strings_exposes_prefix_and_suffix(self) -> None:
        t = WaybillTransformerStrip(prefix="{{ p }}", suffix="{{ s }}")
        pairs = dict(t.template_field_strings())
        assert "{{ p }}" in pairs.values()
        assert "{{ s }}" in pairs.values()
