"""Tests for WaybillTransformerSet."""

from __future__ import annotations

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
