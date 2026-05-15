"""Tests for the build_validator factory."""

from __future__ import annotations

from src.validators import build_validator
from src.validators.count import WaybillValidatorCount
from src.validators.non_empty import WaybillValidatorNonEmpty
from src.validators.regex import WaybillValidatorRegexMatch
from src.types.config import (
    ConfigValidator,
    ValidatorAction,
    ValidatorOperator,
    ValidatorType,
)


def _cfg(
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


class TestBuildValidator:
    def test_builds_non_empty(self) -> None:
        assert isinstance(
            build_validator(_cfg(ValidatorType.NON_EMPTY)), WaybillValidatorNonEmpty
        )

    def test_builds_regex_match(self) -> None:
        assert isinstance(
            build_validator(_cfg(ValidatorType.REGEX_MATCH, pattern=r"^BBC")),
            WaybillValidatorRegexMatch,
        )

    def test_builds_count(self) -> None:
        assert isinstance(
            build_validator(_cfg(ValidatorType.COUNT, value=1)),
            WaybillValidatorCount,
        )

    def test_non_empty_propagates_action_and_field(self) -> None:
        v = build_validator(
            _cfg(ValidatorType.NON_EMPTY, action=ValidatorAction.FAIL, field="tvg_id")
        )
        assert v.action == "fail"
        assert v.field == "tvg_id"  # type: ignore[union-attr]

    def test_regex_match_propagates_pattern_and_field(self) -> None:
        v = build_validator(
            _cfg(ValidatorType.REGEX_MATCH, pattern=r"^NBS", field="tvg_id")
        )
        assert isinstance(v, WaybillValidatorRegexMatch)
        assert v._pattern == r"^NBS"
        assert v.field == "tvg_id"

    def test_count_propagates_operator_and_value(self) -> None:
        v = build_validator(
            _cfg(ValidatorType.COUNT, operator=ValidatorOperator.GTE, value=3)
        )
        assert isinstance(v, WaybillValidatorCount)
        assert v._operator_key == "gte"
        assert v._value == 3

    def test_count_propagates_action(self) -> None:
        v = build_validator(_cfg(ValidatorType.COUNT, action=ValidatorAction.FAIL))
        assert v.action == "fail"
