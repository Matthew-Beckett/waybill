"""Unit tests for the validators package."""

from __future__ import annotations

import sys
import types
from types import SimpleNamespace


# ---------------------------------------------------------------------------
# Stub minimal Django deps required by validator imports
# ---------------------------------------------------------------------------
_channels_models = types.ModuleType("apps.channels.models")
_channels_models.Stream = object  # type: ignore[attr-defined]

for _mod_name, _mod in (
    ("apps", types.ModuleType("apps")),
    ("apps.channels", types.ModuleType("apps.channels")),
    ("apps.channels.models", _channels_models),
):
    if _mod_name not in sys.modules:
        sys.modules[_mod_name] = _mod

from src.validators import build_validator  # noqa: E402
from src.validators.base import WaybillChannelValidatorBase, WaybillStreamValidatorBase  # noqa: E402
from src.validators.count import WaybillValidatorCount  # noqa: E402
from src.validators.non_empty import WaybillValidatorNonEmpty  # noqa: E402
from src.validators.regex import WaybillValidatorRegexMatch  # noqa: E402
from src.types.config import (  # noqa: E402
    ConfigValidator,
    ValidatorAction,
    ValidatorOperator,
    ValidatorType,
)


def _stream(name: str = "Channel 1", tvg_id: str = "ch1.demo") -> SimpleNamespace:
    return SimpleNamespace(name=name, tvg_id=tvg_id, logo_url="")


def _records(count: int = 1) -> list[SimpleNamespace]:
    return [SimpleNamespace(id=i, transformed_name=f"ch{i}") for i in range(count)]


# ---------------------------------------------------------------------------
# WaybillValidatorNonEmpty
# ---------------------------------------------------------------------------


class TestWaybillValidatorNonEmpty:
    def test_passes_when_name_non_empty(self) -> None:
        v = WaybillValidatorNonEmpty(action="warn", field="name")
        assert v.validate(_stream(name="BBC One")) is True

    def test_fails_when_name_empty(self) -> None:
        v = WaybillValidatorNonEmpty(action="warn", field="name")
        assert v.validate(_stream(name="")) is False

    def test_passes_when_tvg_id_non_empty(self) -> None:
        v = WaybillValidatorNonEmpty(action="warn", field="tvg_id")
        assert v.validate(_stream(tvg_id="bbc.one")) is True

    def test_fails_when_tvg_id_empty(self) -> None:
        v = WaybillValidatorNonEmpty(action="warn", field="tvg_id")
        assert v.validate(_stream(tvg_id="")) is False

    def test_action_is_preserved(self) -> None:
        v = WaybillValidatorNonEmpty(action="fail", field="name")
        assert v.action == "fail"

    def test_describe_includes_field_and_action(self) -> None:
        v = WaybillValidatorNonEmpty(action="warn", field="tvg_id")
        desc = v.describe()
        assert "tvg_id" in desc
        assert "warn" in desc

    def test_is_stream_validator(self) -> None:
        v = WaybillValidatorNonEmpty(action="warn", field="name")
        assert isinstance(v, WaybillStreamValidatorBase)


# ---------------------------------------------------------------------------
# WaybillValidatorRegexMatch
# ---------------------------------------------------------------------------


class TestWaybillValidatorRegexMatch:
    def test_passes_when_pattern_matches(self) -> None:
        v = WaybillValidatorRegexMatch(pattern=r"^BBC", action="warn", field="name")
        assert v.validate(_stream(name="BBC One")) is True

    def test_fails_when_pattern_does_not_match(self) -> None:
        v = WaybillValidatorRegexMatch(pattern=r"^BBC", action="warn", field="name")
        assert v.validate(_stream(name="ITV 1")) is False

    def test_pattern_on_tvg_id_field(self) -> None:
        v = WaybillValidatorRegexMatch(
            pattern=r"\.demo$", action="warn", field="tvg_id"
        )
        assert v.validate(_stream(tvg_id="bbc.demo")) is True
        assert v.validate(_stream(tvg_id="bbc.live")) is False

    def test_action_is_preserved(self) -> None:
        v = WaybillValidatorRegexMatch(pattern=r".*", action="fail", field="name")
        assert v.action == "fail"

    def test_describe_includes_pattern_and_action(self) -> None:
        v = WaybillValidatorRegexMatch(pattern=r"^NBS", action="warn", field="name")
        desc = v.describe()
        assert "NBS" in desc
        assert "warn" in desc

    def test_is_stream_validator(self) -> None:
        v = WaybillValidatorRegexMatch(pattern=r".*", action="warn", field="name")
        assert isinstance(v, WaybillStreamValidatorBase)


# ---------------------------------------------------------------------------
# WaybillValidatorCount
# ---------------------------------------------------------------------------


class TestWaybillValidatorCount:
    def test_gt_passes(self) -> None:
        assert WaybillValidatorCount("gt", 0).validate("ch", _records(1)) is True

    def test_gt_fails_when_equal(self) -> None:
        assert WaybillValidatorCount("gt", 1).validate("ch", _records(1)) is False

    def test_gte_passes_when_equal(self) -> None:
        assert WaybillValidatorCount("gte", 1).validate("ch", _records(1)) is True

    def test_gte_fails_below(self) -> None:
        assert WaybillValidatorCount("gte", 2).validate("ch", _records(1)) is False

    def test_lt_passes(self) -> None:
        assert WaybillValidatorCount("lt", 5).validate("ch", _records(3)) is True

    def test_lt_fails_when_equal(self) -> None:
        assert WaybillValidatorCount("lt", 3).validate("ch", _records(3)) is False

    def test_lte_passes_when_equal(self) -> None:
        assert WaybillValidatorCount("lte", 3).validate("ch", _records(3)) is True

    def test_lte_fails_above(self) -> None:
        assert WaybillValidatorCount("lte", 2).validate("ch", _records(3)) is False

    def test_eq_passes(self) -> None:
        assert WaybillValidatorCount("eq", 2).validate("ch", _records(2)) is True

    def test_eq_fails(self) -> None:
        assert WaybillValidatorCount("eq", 2).validate("ch", _records(3)) is False

    def test_neq_passes(self) -> None:
        assert WaybillValidatorCount("neq", 0).validate("ch", _records(2)) is True

    def test_neq_fails_when_equal(self) -> None:
        assert WaybillValidatorCount("neq", 2).validate("ch", _records(2)) is False

    def test_zero_streams(self) -> None:
        assert WaybillValidatorCount("gt", 0).validate("ch", _records(0)) is False
        assert WaybillValidatorCount("eq", 0).validate("ch", _records(0)) is True

    def test_action_is_preserved(self) -> None:
        v = WaybillValidatorCount("gt", 0, action="fail")
        assert v.action == "fail"

    def test_describe_includes_operator_value_and_action(self) -> None:
        v = WaybillValidatorCount("gt", 0, action="warn")
        desc = v.describe()
        assert ">" in desc
        assert "0" in desc
        assert "warn" in desc

    def test_is_channel_validator(self) -> None:
        v = WaybillValidatorCount("gt", 0)
        assert isinstance(v, WaybillChannelValidatorBase)


# ---------------------------------------------------------------------------
# build_validator factory
# ---------------------------------------------------------------------------


class TestBuildValidator:
    def _cfg(
        self,
        validator_type: ValidatorType,
        action: ValidatorAction = ValidatorAction.WARN,
        operator: ValidatorOperator = ValidatorOperator.GT,
        value: int = 0,
        pattern: str = "",
        field: str = "name",
    ) -> ConfigValidator:
        return ConfigValidator(
            type=validator_type,
            action=action,
            operator=operator,
            value=value,
            pattern=pattern,
            field=field,
        )

    def test_builds_non_empty(self) -> None:
        v = build_validator(self._cfg(ValidatorType.NON_EMPTY))
        assert isinstance(v, WaybillValidatorNonEmpty)

    def test_builds_regex_match(self) -> None:
        v = build_validator(self._cfg(ValidatorType.REGEX_MATCH, pattern=r"^BBC"))
        assert isinstance(v, WaybillValidatorRegexMatch)

    def test_builds_count(self) -> None:
        v = build_validator(self._cfg(ValidatorType.COUNT, value=1))
        assert isinstance(v, WaybillValidatorCount)

    def test_non_empty_propagates_action_and_field(self) -> None:
        v = build_validator(
            self._cfg(
                ValidatorType.NON_EMPTY, action=ValidatorAction.FAIL, field="tvg_id"
            )
        )
        assert v.action == "fail"
        assert v.field == "tvg_id"  # type: ignore[union-attr]

    def test_regex_match_propagates_pattern_and_field(self) -> None:
        v = build_validator(
            self._cfg(ValidatorType.REGEX_MATCH, pattern=r"^NBS", field="tvg_id")
        )
        assert isinstance(v, WaybillValidatorRegexMatch)
        assert v._pattern == r"^NBS"
        assert v.field == "tvg_id"

    def test_count_propagates_operator_and_value(self) -> None:
        v = build_validator(
            self._cfg(
                ValidatorType.COUNT,
                operator=ValidatorOperator.GTE,
                value=3,
            )
        )
        assert isinstance(v, WaybillValidatorCount)
        assert v._operator_key == "gte"
        assert v._value == 3

    def test_count_propagates_action(self) -> None:
        v = build_validator(self._cfg(ValidatorType.COUNT, action=ValidatorAction.FAIL))
        assert v.action == "fail"
