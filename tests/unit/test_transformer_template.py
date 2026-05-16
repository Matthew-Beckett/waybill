"""Tests for WaybillTransformerTemplate."""

from __future__ import annotations

import jinja2
import pytest

from src.transformers.template import WaybillTransformerTemplate


class TestWaybillTransformerTemplate:
    @pytest.mark.parametrize(
        "template_str, variables, expected",
        [
            ("{{ ch_name }}", {"ch_name": "Arsenal"}, "Arsenal"),
            (
                "{{ ch_name }} ({{ quality }})",
                {"ch_name": "Arsenal", "quality": "HD"},
                "Arsenal (HD)",
            ),
            ("Fixed Channel", {}, "Fixed Channel"),
        ],
    )
    def test_renders_template(
        self, template_str, variables, expected, stream_factory
    ) -> None:
        t = WaybillTransformerTemplate(value=template_str, field="name")
        s = stream_factory(name="original")
        t.transform(s, variables=variables)
        assert s.name == expected

    def test_renders_to_arbitrary_field(self, stream_factory) -> None:
        t = WaybillTransformerTemplate(value="prefix.{{ id }}", field="tvg_id")
        s = stream_factory(tvg_id="old")
        t.transform(s, variables={"id": "bbc"})
        assert s.tvg_id == "prefix.bbc"

    @pytest.mark.parametrize("variables", [{}, None])
    def test_undefined_variable_raises(self, variables, stream_factory) -> None:
        t = WaybillTransformerTemplate(value="{{ missing }}", field="name")
        s = stream_factory()
        with pytest.raises(jinja2.UndefinedError):
            t.transform(s, variables=variables)

    def test_returns_stream_instance(self, stream_factory) -> None:
        t = WaybillTransformerTemplate(value="static", field="name")
        s = stream_factory()
        assert t.transform(s, variables={}) is s

    @pytest.mark.parametrize(
        "field, expect_in_desc",
        [
            ("name", "template"),
            ("tvg_id", "tvg_id"),
        ],
    )
    def test_describe(self, field, expect_in_desc) -> None:
        t = WaybillTransformerTemplate(value="{{ x }}", field=field)
        assert expect_in_desc in t.describe()
        assert "{{ x }}" in t.describe()

    def test_multiple_renders_are_independent(self, stream_factory) -> None:
        t = WaybillTransformerTemplate(value="{{ ch_name }} ({{ quality }})")
        s1 = stream_factory(name="s1")
        s2 = stream_factory(name="s2")
        t.transform(s1, variables={"ch_name": "Arsenal", "quality": "HD"})
        t.transform(s2, variables={"ch_name": "Chelsea", "quality": "SD"})
        assert s1.name == "Arsenal (HD)"
        assert s2.name == "Chelsea (SD)"
