"""Tests for WaybillMatcherExactMatch."""

from __future__ import annotations

import pytest

from src.matchers.exact_match import WaybillMatcherExactMatch


class TestWaybillMatcherExactMatch:
    @pytest.mark.parametrize(
        "name, values, expected",
        [
            ("BBC One", ["BBC One"], True),  # exact match
            ("BBC One", ["BBC"], False),  # partial string is not an exact match
            ("BBC Three", ["BBC One", "BBC Two"], False),  # not in multi-value list
        ],
    )
    def test_match_result(self, name, values, expected, stream_factory) -> None:
        m = WaybillMatcherExactMatch(values=values, field="name")
        assert m.match(stream_factory(name=name)) is expected

    def test_matches_any_of_multiple_values(self, stream_factory) -> None:
        m = WaybillMatcherExactMatch(values=["BBC One", "BBC Two"], field="name")
        assert m.match(stream_factory(name="BBC Two")) is True
        assert m.match(stream_factory(name="BBC Three")) is False

    @pytest.mark.parametrize(
        "values, case_sensitive, expected",
        [
            (["bbc one"], False, True),  # insensitive → matches
            (["bbc one"], True, False),  # sensitive: lowercase ≠ titlecase
            (["BBC One"], True, True),  # sensitive: exact case
        ],
    )
    def test_case_sensitivity(
        self, values, case_sensitive, expected, stream_factory
    ) -> None:
        m = WaybillMatcherExactMatch(
            values=values, field="name", case_sensitive=case_sensitive
        )
        assert m.match(stream_factory(name="BBC One")) is expected

    def test_drop_action_inverts_result(self, stream_factory) -> None:
        m = WaybillMatcherExactMatch(values=["BBC One"], field="name", action="drop")
        assert m.match(stream_factory(name="BBC One")) is False
        assert m.match(stream_factory(name="ITV 1")) is True

    def test_matches_on_tvg_id_field(self, stream_factory) -> None:
        m = WaybillMatcherExactMatch(values=["bbc.one"], field="tvg_id")
        assert m.match(stream_factory(tvg_id="bbc.one")) is True
        assert m.match(stream_factory(tvg_id="bbc.two")) is False

    def test_empty_values_matches_nothing(self, stream_factory) -> None:
        m = WaybillMatcherExactMatch(values=[], field="name")
        assert m.match(stream_factory(name="BBC One")) is False

    def test_empty_string_value_matches_empty_name(self, stream_factory) -> None:
        m = WaybillMatcherExactMatch(values=[""], field="name")
        assert m.match(stream_factory(name="")) is True
        assert m.match(stream_factory(name="BBC One")) is False

    def test_describe_contains_values_and_field(self) -> None:
        m = WaybillMatcherExactMatch(values=["BBC One", "BBC Two"], field="name")
        desc = m.describe()
        assert "BBC One" in desc
        assert "BBC Two" in desc
        assert "name" in desc

    def test_describe_indicates_case_sensitive(self) -> None:
        m = WaybillMatcherExactMatch(
            values=["BBC One"], field="name", case_sensitive=True
        )
        assert "case-sensitive" in m.describe()
