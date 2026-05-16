"""Tests for WaybillMatcherHasPrefix."""

from __future__ import annotations

import pytest

from src.matchers.has_prefix import WaybillMatcherHasPrefix


class TestWaybillMatcherHasPrefix:
    @pytest.mark.parametrize(
        "name, expected",
        [
            ("NBS News", True),
            ("VTN News", False),
        ],
    )
    def test_match_result(self, name, expected, stream_factory) -> None:
        m = WaybillMatcherHasPrefix(prefixes=["NBS"], field="name")
        assert m.match(stream_factory(name=name)) is expected

    def test_matches_any_of_multiple_prefixes(self, stream_factory) -> None:
        m = WaybillMatcherHasPrefix(prefixes=["NBS", "VTN"], field="name")
        assert m.match(stream_factory(name="VTN 1")) is True
        assert m.match(stream_factory(name="Apex TV")) is False

    @pytest.mark.parametrize(
        "prefixes, case_sensitive, expected",
        [
            (["nbs"], False, True),  # insensitive → matches uppercase value
            (["nbs"], True, False),  # sensitive: lowercase prefix ≠ uppercase value
            (["NBS"], True, True),  # sensitive: exact case matches
        ],
    )
    def test_case_sensitivity(
        self, prefixes, case_sensitive, expected, stream_factory
    ) -> None:
        m = WaybillMatcherHasPrefix(
            prefixes=prefixes, field="name", case_sensitive=case_sensitive
        )
        assert m.match(stream_factory(name="NBS One")) is expected

    def test_drop_action_inverts_result(self, stream_factory) -> None:
        m = WaybillMatcherHasPrefix(prefixes=["NBS"], field="name", action="drop")
        assert m.match(stream_factory(name="NBS One")) is False
        assert m.match(stream_factory(name="VTN 1")) is True

    def test_matches_on_tvg_id_field(self, stream_factory) -> None:
        m = WaybillMatcherHasPrefix(prefixes=["bbc"], field="tvg_id")
        assert m.match(stream_factory(tvg_id="bbc.one")) is True
        assert m.match(stream_factory(tvg_id="itv.one")) is False

    def test_empty_prefixes_matches_nothing(self, stream_factory) -> None:
        m = WaybillMatcherHasPrefix(prefixes=[], field="name")
        assert m.match(stream_factory(name="NBS One")) is False

    def test_describe_contains_prefixes_and_field(self) -> None:
        m = WaybillMatcherHasPrefix(prefixes=["NBS", "VTN"], field="name")
        desc = m.describe()
        assert "NBS" in desc
        assert "VTN" in desc
        assert "name" in desc

    def test_describe_indicates_case_sensitive(self) -> None:
        m = WaybillMatcherHasPrefix(prefixes=["NBS"], field="name", case_sensitive=True)
        assert "case-sensitive" in m.describe()

    def test_renders_template_in_prefix(self, stream_factory) -> None:
        """Template expressions in prefix values are rendered using variables scope."""
        m = WaybillMatcherHasPrefix(prefixes=["{{ provider }}|"], field="name")
        matched, _ = m.match_and_capture(
            stream_factory(name="UK| NBS One"),
            variables={"provider": "UK"},
        )
        assert matched is True

    def test_template_prefix_no_match_when_variable_differs(
        self, stream_factory
    ) -> None:
        m = WaybillMatcherHasPrefix(prefixes=["{{ provider }}|"], field="name")
        matched, _ = m.match_and_capture(
            stream_factory(name="UK| NBS One"),
            variables={"provider": "US"},
        )
        assert matched is False
