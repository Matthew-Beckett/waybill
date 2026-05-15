"""Tests for WaybillMatcherRegex."""

from __future__ import annotations

import pytest

from src.matchers.regex import WaybillMatcherRegex


class TestWaybillMatcherRegex:
    @pytest.mark.parametrize(
        "name, expected",
        [
            ("BBC One", True),
            ("ITV 1", False),
        ],
    )
    def test_match_result(self, name, expected, stream_factory) -> None:
        m = WaybillMatcherRegex(pattern=r"^BBC", field="name")
        assert m.match(stream_factory(name=name)) is expected

    @pytest.mark.parametrize(
        "pattern, case_sensitive, expected",
        [
            (r"^bbc", False, True),  # insensitive → matches uppercase value
            (r"^bbc", True, False),  # sensitive: lowercase pattern ≠ uppercase value
            (r"^BBC", True, True),  # sensitive: exact case matches
        ],
    )
    def test_case_sensitivity(
        self, pattern, case_sensitive, expected, stream_factory
    ) -> None:
        m = WaybillMatcherRegex(
            pattern=pattern, field="name", case_sensitive=case_sensitive
        )
        assert m.match(stream_factory(name="BBC One")) is expected

    def test_drop_action_inverts_result(self, stream_factory) -> None:
        m = WaybillMatcherRegex(pattern=r"^BBC", field="name", action="drop")
        assert m.match(stream_factory(name="BBC One")) is False
        assert m.match(stream_factory(name="ITV 1")) is True

    def test_matches_on_tvg_id_field(self, stream_factory) -> None:
        m = WaybillMatcherRegex(pattern=r".*\.demo$", field="tvg_id")
        assert m.match(stream_factory(tvg_id="bbc.demo")) is True
        assert m.match(stream_factory(tvg_id="bbc.live")) is False

    def test_empty_pattern_matches_everything(self, stream_factory) -> None:
        m = WaybillMatcherRegex(pattern=r"", field="name")
        assert m.match(stream_factory(name="Anything")) is True

    def test_describe_contains_field_and_pattern(self) -> None:
        m = WaybillMatcherRegex(pattern=r"^BBC", field="name")
        assert "name" in m.describe()
        assert "^BBC" in m.describe()

    def test_describe_includes_drop_action(self) -> None:
        m = WaybillMatcherRegex(pattern=r"^BBC", field="name", action="drop")
        assert "drop" in m.describe()
