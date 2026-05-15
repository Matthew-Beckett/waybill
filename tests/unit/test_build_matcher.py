"""Tests for the build_matcher factory."""

from __future__ import annotations

from src.matchers import build_matcher
from src.matchers.contains_any import WaybillMatcherContainsAny
from src.matchers.exact_match import WaybillMatcherExactMatch
from src.matchers.has_prefix import WaybillMatcherHasPrefix
from src.matchers.regex import WaybillMatcherRegex
from src.types.config import ConfigMatcher, MatcherAction, MatcherType


def _cfg(
    matcher_type: MatcherType,
    action: MatcherAction = MatcherAction.KEEP,
    pattern: str = r".*",
    prefixes: list[str] | None = None,
    substrings: list[str] | None = None,
    values: list[str] | None = None,
    case_sensitive: bool = False,
    field: str = "name",
) -> ConfigMatcher:
    return ConfigMatcher(
        type=matcher_type,
        action=action,
        pattern=pattern,
        prefixes=prefixes or [],
        substrings=substrings or [],
        values=values or [],
        case_sensitive=case_sensitive,
        field=field,
    )


class TestBuildMatcher:
    def test_builds_regex_matcher(self) -> None:
        assert isinstance(build_matcher(_cfg(MatcherType.REGEX)), WaybillMatcherRegex)

    def test_builds_has_prefix_matcher(self) -> None:
        assert isinstance(
            build_matcher(_cfg(MatcherType.HAS_PREFIX, prefixes=["BBC"])),
            WaybillMatcherHasPrefix,
        )

    def test_builds_contains_any_matcher(self) -> None:
        assert isinstance(
            build_matcher(_cfg(MatcherType.CONTAINS_ANY, substrings=["News"])),
            WaybillMatcherContainsAny,
        )

    def test_builds_exact_match_matcher(self) -> None:
        assert isinstance(
            build_matcher(_cfg(MatcherType.EXACT_MATCH, values=["BBC One"])),
            WaybillMatcherExactMatch,
        )

    def test_propagates_drop_action(self) -> None:
        m = build_matcher(_cfg(MatcherType.REGEX, action=MatcherAction.DROP))
        assert m.action == "drop"

    def test_propagates_field(self) -> None:
        m = build_matcher(_cfg(MatcherType.REGEX, field="tvg_id"))
        assert m.field == "tvg_id"

    def test_propagates_case_sensitive(self) -> None:
        m = build_matcher(_cfg(MatcherType.REGEX, case_sensitive=True))
        assert m.case_sensitive is True

    def test_regex_propagates_pattern(self) -> None:
        m = build_matcher(_cfg(MatcherType.REGEX, pattern=r"^BBC"))
        assert isinstance(m, WaybillMatcherRegex)
        assert m.pattern == r"^BBC"

    def test_has_prefix_propagates_prefixes(self) -> None:
        m = build_matcher(_cfg(MatcherType.HAS_PREFIX, prefixes=["BBC", "ITV"]))
        assert isinstance(m, WaybillMatcherHasPrefix)
        assert m._display_prefixes == ["BBC", "ITV"]

    def test_contains_any_propagates_substrings(self) -> None:
        m = build_matcher(_cfg(MatcherType.CONTAINS_ANY, substrings=["News", "Sport"]))
        assert isinstance(m, WaybillMatcherContainsAny)
        assert m._display_substrings == ["News", "Sport"]

    def test_exact_match_propagates_values(self) -> None:
        m = build_matcher(_cfg(MatcherType.EXACT_MATCH, values=["BBC One", "BBC Two"]))
        assert isinstance(m, WaybillMatcherExactMatch)
        assert m._display_values == ["BBC One", "BBC Two"]
