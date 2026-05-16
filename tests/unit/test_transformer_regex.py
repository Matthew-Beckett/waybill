"""Tests for WaybillTransformerRegex."""

from __future__ import annotations

import pytest

from src.transformers.regex import WaybillTransformerRegex


@pytest.fixture()
def stream(stream_factory):
    return stream_factory()


class TestWaybillTransformerRegex:
    def test_replace_substitutes_matched_text(self, stream_factory) -> None:
        t = WaybillTransformerRegex(pattern=r"^UK: ", action="replace", replacement="")
        s = stream_factory(name="UK: BBC One")
        result = t.transform(s)
        assert result is s
        assert s.name == "BBC One"

    def test_replace_with_backreference(self, stream_factory) -> None:
        t = WaybillTransformerRegex(
            pattern=r"^(\w+).*", action="replace", replacement="$1"
        )
        s = stream_factory(name="BBC One HD")
        t.transform(s)
        assert s.name == "BBC"

    def test_replace_no_match_leaves_name_unchanged(self, stream_factory) -> None:
        t = WaybillTransformerRegex(pattern=r"^XYZ", action="replace", replacement="")
        s = stream_factory(name="BBC One")
        t.transform(s)
        assert s.name == "BBC One"

    def test_drop_returns_none_when_pattern_matches(self, stream_factory) -> None:
        t = WaybillTransformerRegex(pattern=r"HD$", action="drop")
        assert t.transform(stream_factory(name="BBC One HD")) is None

    def test_drop_returns_stream_when_pattern_does_not_match(
        self, stream_factory
    ) -> None:
        t = WaybillTransformerRegex(pattern=r"HD$", action="drop")
        s = stream_factory(name="BBC One SD")
        assert t.transform(s) is s

    def test_replace_on_tvg_id_field(self, stream_factory) -> None:
        t = WaybillTransformerRegex(
            pattern=r"\.demo$", action="replace", replacement=".live", field="tvg_id"
        )
        s = stream_factory(tvg_id="bbc.demo")
        t.transform(s)
        assert s.tvg_id == "bbc.live"

    def test_drop_on_tvg_id_field(self, stream_factory) -> None:
        t = WaybillTransformerRegex(pattern=r"\.demo$", action="drop", field="tvg_id")
        assert t.transform(stream_factory(tvg_id="bbc.demo")) is None

    def test_unknown_action_raises(self, stream_factory) -> None:
        t = WaybillTransformerRegex(pattern=r".*", action="explode")
        with pytest.raises(ValueError, match="explode"):
            t.transform(stream_factory())

    def test_dollar_backreferences_converted_to_python_style(
        self, stream_factory
    ) -> None:
        t = WaybillTransformerRegex(
            pattern=r"(\w+) (\w+)", action="replace", replacement="$2 $1"
        )
        s = stream_factory(name="Hello World")
        t.transform(s)
        assert s.name == "World Hello"

    def test_replace_global_substitution(self, stream_factory) -> None:
        t = WaybillTransformerRegex(pattern=r"\s+", action="replace", replacement=" ")
        s = stream_factory(name="BBC   One    HD")
        t.transform(s)
        assert s.name == "BBC One HD"

    def test_renders_template_in_replacement(self, stream_factory) -> None:
        t = WaybillTransformerRegex(
            pattern=r"^DEMO\| ", action="replace", replacement="{{ prefix }}: "
        )
        s = stream_factory(name="DEMO| BBC One")
        t.transform(s, variables={"prefix": "UK"})
        assert s.name == "UK: BBC One"

    def test_renders_template_in_pattern(self, stream_factory) -> None:
        t = WaybillTransformerRegex(
            pattern=r"^{{ strip_prefix }}\| ", action="replace", replacement=""
        )
        s = stream_factory(name="UK| BBC One")
        t.transform(s, variables={"strip_prefix": "UK"})
        assert s.name == "BBC One"

    def test_undefined_template_variable_raises(self, stream_factory) -> None:
        t = WaybillTransformerRegex(
            pattern=r"^{{ missing }}\| ", action="replace", replacement=""
        )
        s = stream_factory(name="UK| BBC One")
        with pytest.raises(ValueError, match="Undefined template variable"):
            t.transform(s, variables={})

    def test_template_field_strings_exposes_pattern_and_replacement(self) -> None:
        t = WaybillTransformerRegex(
            pattern=r"^{{ p }}", action="replace", replacement="{{ r }}"
        )
        pairs = dict(t.template_field_strings())
        assert r"^{{ p }}" in pairs.values()
        assert "{{ r }}" in pairs.values()

    def test_describe_replace(self) -> None:
        t = WaybillTransformerRegex(pattern=r"^UK: ", action="replace", replacement="")
        desc = t.describe()
        assert "UK: " in desc
        assert "replace" in desc or "→" in desc

    def test_describe_drop(self) -> None:
        t = WaybillTransformerRegex(pattern=r"HD$", action="drop")
        desc = t.describe()
        assert "HD$" in desc
        assert "drop" in desc

    def test_describe_includes_field_when_not_name(self) -> None:
        t = WaybillTransformerRegex(
            pattern=r".*", action="replace", replacement="", field="tvg_id"
        )
        assert "tvg_id" in t.describe()
