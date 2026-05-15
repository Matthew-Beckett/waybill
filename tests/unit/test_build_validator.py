"""Tests for the build_validator factory."""

from __future__ import annotations

import pytest

from src.types.config import (
    ConfigValidator,
    ValidatorAction,
    ValidatorOperator,
    ValidatorScope,
    ValidatorType,
)
from src.validators import build_validator
from src.validators.count import (
    WaybillValidatorCountChannel,
    WaybillValidatorCountMember,
)
from src.validators.non_empty import (
    WaybillValidatorNonEmpty,
    WaybillValidatorNonEmptyChannel,
)
from src.validators.regex import (
    WaybillValidatorRegexMatch,
    WaybillValidatorRegexMatchChannel,
)


def _cfg(
    validator_type: ValidatorType,
    action: ValidatorAction = ValidatorAction.WARN,
    operator: ValidatorOperator = ValidatorOperator.GT,
    value: int = 0,
    pattern: str = "",
    scope: ValidatorScope | None = None,
    field: str = "name",
) -> ConfigValidator:
    return ConfigValidator(
        type=validator_type,
        action=action,
        operator=operator,
        value=value,
        pattern=pattern,
        scope=scope,
        field=field,
    )


class TestBuildValidator:
    @pytest.mark.parametrize(
        ("validator_type", "scope", "expected_cls", "kwargs"),
        [
            (ValidatorType.NON_EMPTY, None, WaybillValidatorNonEmpty, {}),
            (
                ValidatorType.NON_EMPTY,
                ValidatorScope.STREAM,
                WaybillValidatorNonEmpty,
                {},
            ),
            (
                ValidatorType.NON_EMPTY,
                ValidatorScope.CHANNEL,
                WaybillValidatorNonEmptyChannel,
                {},
            ),
            (
                ValidatorType.REGEX_MATCH,
                None,
                WaybillValidatorRegexMatch,
                {"pattern": r"^BBC"},
            ),
            (
                ValidatorType.REGEX_MATCH,
                ValidatorScope.STREAM,
                WaybillValidatorRegexMatch,
                {"pattern": r"^BBC"},
            ),
            (
                ValidatorType.REGEX_MATCH,
                ValidatorScope.CHANNEL,
                WaybillValidatorRegexMatchChannel,
                {"pattern": r"^BBC"},
            ),
            (ValidatorType.COUNT, None, WaybillValidatorCountMember, {"value": 1}),
            (
                ValidatorType.COUNT,
                ValidatorScope.CHANNEL,
                WaybillValidatorCountChannel,
                {"operator": ValidatorOperator.GT, "value": 2},
            ),
        ],
    )
    def test_builds_expected_validator(
        self,
        validator_type: ValidatorType,
        scope: ValidatorScope | None,
        expected_cls: type,
        kwargs: dict[str, object],
    ) -> None:
        assert isinstance(
            build_validator(_cfg(validator_type, scope=scope, **kwargs)),
            expected_cls,
        )

    def test_non_empty_propagates_action_and_field(self) -> None:
        validator = build_validator(
            _cfg(ValidatorType.NON_EMPTY, action=ValidatorAction.FAIL, field="tvg_id")
        )
        assert validator.action == "fail"
        assert validator.field == "tvg_id"  # type: ignore[union-attr]

    def test_regex_match_propagates_pattern_and_field(self) -> None:
        validator = build_validator(
            _cfg(ValidatorType.REGEX_MATCH, pattern=r"^NBS", field="tvg_id")
        )
        assert isinstance(validator, WaybillValidatorRegexMatch)
        assert validator._pattern == r"^NBS"
        assert validator.field == "tvg_id"

    def test_count_propagates_operator_and_value(self) -> None:
        validator = build_validator(
            _cfg(ValidatorType.COUNT, operator=ValidatorOperator.GTE, value=3)
        )
        assert isinstance(validator, WaybillValidatorCountMember)
        assert validator._operator_key == "gte"
        assert validator._value == 3

    def test_count_propagates_action(self) -> None:
        validator = build_validator(
            _cfg(ValidatorType.COUNT, action=ValidatorAction.FAIL)
        )
        assert validator.action == "fail"

    @pytest.mark.parametrize(
        ("validator_type", "scope", "kwargs", "message"),
        [
            (
                ValidatorType.NON_EMPTY,
                ValidatorScope.MEMBER,
                {"field": "tvg_id"},
                "nonEmpty validators only support stream or channel scope",
            ),
            (
                ValidatorType.REGEX_MATCH,
                ValidatorScope.MEMBER,
                {"pattern": r"^NBS", "field": "name"},
                "regexMatch validators only support stream or channel scope",
            ),
            (
                ValidatorType.COUNT,
                ValidatorScope.STREAM,
                {"value": 1},
                "count validators only support member or channel scope",
            ),
        ],
    )
    def test_unsupported_scope_raises(
        self,
        validator_type: ValidatorType,
        scope: ValidatorScope,
        kwargs: dict[str, object],
        message: str,
    ) -> None:
        with pytest.raises(ValueError, match=message):
            build_validator(_cfg(validator_type, scope=scope, **kwargs))
