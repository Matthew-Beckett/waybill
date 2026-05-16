"""Tests for WaybillMatcherExactMatch."""

from __future__ import annotations

import pytest

from src.matchers.exact_match import WaybillMatcherExactMatch


class TestWaybillMatcherExactMatch:
    @pytest.mark.parametrize(
        "name, values, expected",
        [
            ("NBS One", ["NBS One"], True),  # exact match
            ("NBS One", ["NBS"], False),  # partial string is not an exact match
            ("NBS Three", ["NBS One", "NBS Two"], False),  # not in multi-value list
        ],
    )
    def test_match_result(self, name, values, expected, stream_factory) -> None:
        m = WaybillMatcherExactMatch(values=values, field="name")
        assert m.match(stream_factory(name=name)) is expected

    def test_matches_any_of_multiple_values(self, stream_factory) -> None:
        m = WaybillMatcherExactMatch(values=["NBS One", "NBS Two"], field="name")
        assert m.match(stream_factory(name="NBS Two")) is True
        assert m.match(stream_factory(name="NBS Three")) is False

    @pytest.mark.parametrize(
        "values, case_sensitive, expected",
        [
            (["nbs one"], False, True),  # insensitive → matches
            (["nbs one"], True, False),  # sensitive: lowercase ≠ titlecase
            (["NBS One"], True, True),  # sensitive: exact case
        ],
    )
    def test_case_sensitivity(
        self, values, case_sensitive, expected, stream_factory
    ) -> None:
        m = WaybillMatcherExactMatch(
            values=values, field="name", case_sensitive=case_sensitive
        )
        assert m.match(stream_factory(name="NBS One")) is expected

    def test_drop_action_inverts_result(self, stream_factory) -> None:
        m = WaybillMatcherExactMatch(values=["NBS One"], field="name", action="drop")
        assert m.match(stream_factory(name="NBS One")) is False
        assert m.match(stream_factory(name="VTN 1")) is True

    def test_matches_on_tvg_id_field(self, stream_factory) -> None:
        m = WaybillMatcherExactMatch(values=["bbc.one"], field="tvg_id")
        assert m.match(stream_factory(tvg_id="bbc.one")) is True
        assert m.match(stream_factory(tvg_id="bbc.two")) is False

    def test_empty_values_matches_nothing(self, stream_factory) -> None:
        m = WaybillMatcherExactMatch(values=[], field="name")
        assert m.match(stream_factory(name="NBS One")) is False

    def test_empty_string_value_matches_empty_name(self, stream_factory) -> None:
        m = WaybillMatcherExactMatch(values=[""], field="name")
        assert m.match(stream_factory(name="")) is True
        assert m.match(stream_factory(name="NBS One")) is False

    def test_describe_contains_values_and_field(self) -> None:
        m = WaybillMatcherExactMatch(values=["NBS One", "NBS Two"], field="name")
        desc = m.describe()
        assert "NBS One" in desc
        assert "NBS Two" in desc
        assert "name" in desc

    def test_describe_indicates_case_sensitive(self) -> None:
        m = WaybillMatcherExactMatch(
            values=["NBS One"], field="name", case_sensitive=True
        )
        assert "case-sensitive" in m.describe()

    def test_renders_template_in_value(self, stream_factory) -> None:
        """Template expressions in values are rendered using variables scope."""
        m = WaybillMatcherExactMatch(values=["{{ provider }}| NBS One"], field="name")
        matched, _ = m.match_and_capture(
            stream_factory(name="UK| NBS One"),
            variables={"provider": "UK"},
        )
        assert matched is True

    def test_template_value_no_match_when_variable_differs(
        self, stream_factory
    ) -> None:
        m = WaybillMatcherExactMatch(values=["{{ provider }}| NBS One"], field="name")
        matched, _ = m.match_and_capture(
            stream_factory(name="UK| NBS One"),
            variables={"provider": "US"},
        )
        assert matched is False
