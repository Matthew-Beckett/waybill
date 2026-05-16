"""Tests for WaybillTransformerSet."""

from __future__ import annotations

import pytest

from src.transformers.set import WaybillTransformerSet


class TestWaybillTransformerSet:
    def test_sets_field_to_fixed_value(self, stream_factory) -> None:
        t = WaybillTransformerSet(value="BBC One", field="name")
        s = stream_factory(name="Old Name")
        t.transform(s)
        assert s.name == "BBC One"

    def test_sets_tvg_id_field(self, stream_factory) -> None:
        t = WaybillTransformerSet(value="bbc.one", field="tvg_id")
        s = stream_factory(tvg_id="old.id")
        t.transform(s)
        assert s.tvg_id == "bbc.one"

    def test_returns_stream_instance(self, stream_factory) -> None:
        t = WaybillTransformerSet(value="BBC One")
        s = stream_factory()
        assert t.transform(s) is s

    def test_overwrites_any_existing_value(self, stream_factory) -> None:
        t = WaybillTransformerSet(value="Canonical Name")
        for original in ("", "A", "Some Long Name 1"):
            s = stream_factory(name=original)
            t.transform(s)
            assert s.name == "Canonical Name"

    def test_set_empty_string_value(self, stream_factory) -> None:
        t = WaybillTransformerSet(value="")
        s = stream_factory(name="BBC One")
        t.transform(s)
        assert s.name == ""

    def test_describe_contains_value_and_field(self) -> None:
        t = WaybillTransformerSet(value="BBC One", field="name")
        desc = t.describe()
        assert "BBC One" in desc
        assert "name" in desc

    def test_renders_template_expression_in_value(self, stream_factory) -> None:
        t = WaybillTransformerSet(value="{{ brand }} One", field="name")
        s = stream_factory(name="old")
        t.transform(s, variables={"brand": "BBC"})
        assert s.name == "BBC One"

    def test_template_on_non_name_field(self, stream_factory) -> None:
        t = WaybillTransformerSet(value="{{ prefix }}.one", field="tvg_id")
        s = stream_factory(tvg_id="old.id")
        t.transform(s, variables={"prefix": "bbc"})
        assert s.tvg_id == "bbc.one"

    def test_undefined_template_variable_raises(self, stream_factory) -> None:
        t = WaybillTransformerSet(value="{{ missing }}", field="name")
        s = stream_factory()
        with pytest.raises(ValueError, match="Undefined template variable"):
            t.transform(s, variables={})

    def test_template_field_strings_exposes_value(self) -> None:
        t = WaybillTransformerSet(value="{{ brand }} One", field="name")
        pairs = t.template_field_strings()
        assert len(pairs) == 1
        assert pairs[0][1] == "{{ brand }} One"
