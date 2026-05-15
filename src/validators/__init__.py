from ..types.config import ConfigValidator, ValidatorScope, ValidatorType
from .base import (
    WaybillChannelValidatorBase,
    WaybillMemberValidatorBase,
    WaybillStreamValidatorBase,
)
from .count import WaybillValidatorCountChannel, WaybillValidatorCountMember
from .non_empty import WaybillValidatorNonEmpty, WaybillValidatorNonEmptyChannel
from .regex import WaybillValidatorRegexMatch, WaybillValidatorRegexMatchChannel


def build_validator(
    cfg: ConfigValidator,
) -> (
    WaybillStreamValidatorBase
    | WaybillChannelValidatorBase
    | WaybillMemberValidatorBase
):
    """Instantiate the appropriate validator from a ConfigValidator."""
    action = cfg.action.value

    if cfg.type is ValidatorType.NON_EMPTY:
        effective_scope = cfg.scope or ValidatorScope.STREAM
        if effective_scope is ValidatorScope.MEMBER:
            raise ValueError("nonEmpty validators only support stream or channel scope")
        if effective_scope is ValidatorScope.CHANNEL:
            return WaybillValidatorNonEmptyChannel(action=action, field=cfg.field)
        return WaybillValidatorNonEmpty(action=action, field=cfg.field)

    if cfg.type is ValidatorType.REGEX_MATCH:
        effective_scope = cfg.scope or ValidatorScope.STREAM
        if effective_scope is ValidatorScope.MEMBER:
            raise ValueError(
                "regexMatch validators only support stream or channel scope"
            )
        if effective_scope is ValidatorScope.CHANNEL:
            return WaybillValidatorRegexMatchChannel(
                pattern=cfg.pattern, action=action, field=cfg.field
            )
        return WaybillValidatorRegexMatch(
            pattern=cfg.pattern, action=action, field=cfg.field
        )

    if cfg.type is ValidatorType.COUNT:
        effective_scope = cfg.scope or ValidatorScope.MEMBER
        if effective_scope is ValidatorScope.STREAM:
            raise ValueError("count validators only support member or channel scope")
        if effective_scope is ValidatorScope.CHANNEL:
            return WaybillValidatorCountChannel(
                operator=cfg.operator.value, value=cfg.value, action=action
            )
        return WaybillValidatorCountMember(
            operator=cfg.operator.value, value=cfg.value, action=action
        )

    raise ValueError(f"Unknown validator type: {cfg.type!r}")
