"""Tests for WaybillMatcherContainsAny."""

from __future__ import annotations

import pytest

from src.matchers.contains_any import WaybillMatcherContainsAny


class TestWaybillMatcherContainsAny:
    @pytest.mark.parametrize(
        "name, expected",
        [
            ("BBC News", True),
            ("BBC Sport", False),
        ],
    )
    def test_match_result(self, name, expected, stream_factory) -> None:
        m = WaybillMatcherContainsAny(substrings=["News"], field="name")
        assert m.match(stream_factory(name=name)) is expected

    def test_matches_any_of_multiple_substrings(self, stream_factory) -> None:
        m = WaybillMatcherContainsAny(substrings=["News", "Sport"], field="name")
        assert m.match(stream_factory(name="BBC Sport")) is True
        assert m.match(stream_factory(name="BBC One")) is False

    @pytest.mark.parametrize(
        "substrings, case_sensitive, expected",
        [
            (["news"], False, True),  # insensitive → matches
            (["news"], True, False),  # sensitive: lowercase ≠ titlecase
            (["News"], True, True),  # sensitive: exact case
        ],
    )
    def test_case_sensitivity(
        self, substrings, case_sensitive, expected, stream_factory
    ) -> None:
        m = WaybillMatcherContainsAny(
            substrings=substrings, field="name", case_sensitive=case_sensitive
        )
        assert m.match(stream_factory(name="BBC News")) is expected

    def test_drop_action_inverts_result(self, stream_factory) -> None:
        m = WaybillMatcherContainsAny(substrings=["News"], field="name", action="drop")
        assert m.match(stream_factory(name="BBC News")) is False
        assert m.match(stream_factory(name="BBC One")) is True

    def test_matches_on_tvg_id_field(self, stream_factory) -> None:
        m = WaybillMatcherContainsAny(substrings=["demo"], field="tvg_id")
        assert m.match(stream_factory(tvg_id="bbc.demo")) is True
        assert m.match(stream_factory(tvg_id="bbc.live")) is False

    def test_empty_substrings_matches_nothing(self, stream_factory) -> None:
        m = WaybillMatcherContainsAny(substrings=[], field="name")
        assert m.match(stream_factory(name="BBC News")) is False

    @pytest.mark.parametrize(
        "name, substring",
        [
            ("BBC One", "BBC"),  # substring at start
            ("BBC One HD", "HD"),  # substring at end
        ],
    )
    def test_substring_position(self, name, substring, stream_factory) -> None:
        m = WaybillMatcherContainsAny(substrings=[substring], field="name")
        assert m.match(stream_factory(name=name)) is True

    def test_describe_contains_substrings_and_field(self) -> None:
        m = WaybillMatcherContainsAny(substrings=["News", "Sport"], field="name")
        desc = m.describe()
        assert "News" in desc
        assert "Sport" in desc
        assert "name" in desc

    def test_describe_indicates_case_sensitive(self) -> None:
        m = WaybillMatcherContainsAny(
            substrings=["news"], field="name", case_sensitive=True
        )
        assert "case-sensitive" in m.describe()

    def test_renders_template_in_substring(self, stream_factory) -> None:
        """Template expressions in substring values are rendered using variables scope."""
        m = WaybillMatcherContainsAny(substrings=["{{ keyword }}"], field="name")
        matched, _ = m.match_and_capture(
            stream_factory(name="BBC News"),
            variables={"keyword": "News"},
        )
        assert matched is True

    def test_template_substring_no_match_when_variable_differs(
        self, stream_factory
    ) -> None:
        m = WaybillMatcherContainsAny(substrings=["{{ keyword }}"], field="name")
        matched, _ = m.match_and_capture(
            stream_factory(name="BBC News"),
            variables={"keyword": "Sport"},
        )
        assert matched is False
