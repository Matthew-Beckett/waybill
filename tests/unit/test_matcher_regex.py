"""Tests for WaybillMatcherRegex."""

from __future__ import annotations

import pytest

from src.matchers.regex import WaybillMatcherRegex


class TestWaybillMatcherRegex:
    @pytest.mark.parametrize(
        "name, expected",
        [
            ("NBS One", True),
            ("VTN 1", False),
        ],
    )
    def test_match_result(self, name, expected, stream_factory) -> None:
        m = WaybillMatcherRegex(pattern=r"^NBS", field="name")
        assert m.match(stream_factory(name=name)) is expected

    @pytest.mark.parametrize(
        "pattern, case_sensitive, expected",
        [
            (r"^nbs", False, True),  # insensitive → matches uppercase value
            (r"^nbs", True, False),  # sensitive: lowercase pattern ≠ uppercase value
            (r"^NBS", True, True),  # sensitive: exact case matches
        ],
    )
    def test_case_sensitivity(
        self, pattern, case_sensitive, expected, stream_factory
    ) -> None:
        m = WaybillMatcherRegex(
            pattern=pattern, field="name", case_sensitive=case_sensitive
        )
        assert m.match(stream_factory(name="NBS One")) is expected

    def test_drop_action_inverts_result(self, stream_factory) -> None:
        m = WaybillMatcherRegex(pattern=r"^NBS", field="name", action="drop")
        assert m.match(stream_factory(name="NBS One")) is False
        assert m.match(stream_factory(name="VTN 1")) is True

    def test_matches_on_tvg_id_field(self, stream_factory) -> None:
        m = WaybillMatcherRegex(pattern=r".*\.demo$", field="tvg_id")
        assert m.match(stream_factory(tvg_id="bbc.demo")) is True
        assert m.match(stream_factory(tvg_id="bbc.live")) is False

    def test_empty_pattern_matches_everything(self, stream_factory) -> None:
        m = WaybillMatcherRegex(pattern=r"", field="name")
        assert m.match(stream_factory(name="Anything")) is True

    def test_describe_contains_field_and_pattern(self) -> None:
        m = WaybillMatcherRegex(pattern=r"^NBS", field="name")
        assert "name" in m.describe()
        assert "^NBS" in m.describe()

    def test_describe_includes_drop_action(self) -> None:
        m = WaybillMatcherRegex(pattern=r"^NBS", field="name", action="drop")
        assert "drop" in m.describe()


class TestWaybillMatcherRegexCapture:
    """Tests for WaybillMatcherRegex.match_and_capture()."""

    def test_named_groups_returned_on_match(self, stream_factory) -> None:
        m = WaybillMatcherRegex(
            pattern=r"^UK\| (?P<ch_name>.+?) (?P<quality>HD|SD)$", field="name"
        )
        matched, captures = m.match_and_capture(stream_factory(name="UK| Northgate HD"))
        assert matched is True
        assert captures == {"ch_name": "Northgate", "quality": "HD"}

    def test_no_named_groups_returns_empty_dict(self, stream_factory) -> None:
        m = WaybillMatcherRegex(pattern=r"^UK\|", field="name")
        matched, captures = m.match_and_capture(stream_factory(name="UK| NBS One"))
        assert matched is True
        assert captures == {}

    def test_no_match_returns_false_empty_dict(self, stream_factory) -> None:
        m = WaybillMatcherRegex(pattern=r"^UK\| (?P<ch_name>.+)$", field="name")
        matched, captures = m.match_and_capture(stream_factory(name="US| ESPN"))
        assert matched is False
        assert captures == {}

    @pytest.mark.parametrize(
        "stream_name, expected_matched",
        [
            ("UK| Northgate HD", False),  # matches pattern → dropped
            ("US| ESPN", True),  # no match → kept, no captures
        ],
        ids=["match_drops", "no_match_keeps"],
    )
    def test_drop_action(self, stream_name, expected_matched, stream_factory) -> None:
        m = WaybillMatcherRegex(
            pattern=r"^UK\| (?P<ch_name>.+)$", field="name", action="drop"
        )
        matched, captures = m.match_and_capture(stream_factory(name=stream_name))
        assert matched is expected_matched
        assert captures == {}

    def test_case_insensitive_captures(self, stream_factory) -> None:
        m = WaybillMatcherRegex(
            pattern=r"^uk\| (?P<ch_name>.+?) (?P<quality>hd|sd)$",
            field="name",
            case_sensitive=False,
        )
        matched, captures = m.match_and_capture(stream_factory(name="UK| Northgate HD"))
        assert matched is True
        assert captures["ch_name"] == "Northgate"

    def test_optional_group_absent_not_in_captures(self, stream_factory) -> None:
        """Named groups whose match is None (optional group absent) are excluded."""
        m = WaybillMatcherRegex(
            pattern=r"^(?P<ch_name>.+?)(?P<quality> HD)?$", field="name"
        )
        matched, captures = m.match_and_capture(stream_factory(name="Northgate"))
        assert matched is True
        # quality group matched nothing; absent from captures
        assert "quality" not in captures
        assert captures["ch_name"] == "Northgate"

    @pytest.mark.parametrize(
        "pattern, expect_captures_annotation, expected_names",
        [
            (
                r"^UK\| (?P<ch_name>.+?) (?P<quality>HD|SD)$",
                True,
                ["ch_name", "quality"],
            ),
            (r"^UK\|", False, []),
        ],
        ids=["with_named_groups", "no_named_groups"],
    )
    def test_describe_named_groups(
        self, pattern, expect_captures_annotation, expected_names
    ) -> None:
        m = WaybillMatcherRegex(pattern=pattern, field="name")
        desc = m.describe()
        assert ("captures" in desc) is expect_captures_annotation
        for name in expected_names:
            assert name in desc

    def test_renders_template_in_pattern_with_variables(self, stream_factory) -> None:
        """Template expressions in the pattern are rendered using the variables scope."""
        m = WaybillMatcherRegex(
            pattern=r"^{{ provider }}\| (?P<ch_name>.+)$", field="name"
        )
        matched, captures = m.match_and_capture(
            stream_factory(name="UK| Northgate"),
            variables={"provider": "UK"},
        )
        assert matched is True
        assert captures["ch_name"] == "Northgate"

    def test_template_in_pattern_no_match_when_variable_differs(
        self, stream_factory
    ) -> None:
        m = WaybillMatcherRegex(
            pattern=r"^{{ provider }}\| (?P<ch_name>.+)$", field="name"
        )
        matched, _ = m.match_and_capture(
            stream_factory(name="UK| Northgate"),
            variables={"provider": "US"},
        )
        assert matched is False
