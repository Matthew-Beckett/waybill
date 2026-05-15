from ..types.config import ConfigValidator, ValidatorType
from .base import WaybillChannelValidatorBase, WaybillStreamValidatorBase
from .count import WaybillValidatorCount
from .non_empty import WaybillValidatorNonEmpty
from .regex import WaybillValidatorRegexMatch


def build_validator(
    cfg: ConfigValidator,
) -> WaybillStreamValidatorBase | WaybillChannelValidatorBase:
    """Instantiate the appropriate validator from a ConfigValidator."""
    action = cfg.action.value

    if cfg.type is ValidatorType.NON_EMPTY:
        return WaybillValidatorNonEmpty(action=action, field=cfg.field)

    if cfg.type is ValidatorType.REGEX_MATCH:
        return WaybillValidatorRegexMatch(
            pattern=cfg.pattern, action=action, field=cfg.field
        )

    if cfg.type is ValidatorType.COUNT:
        return WaybillValidatorCount(
            operator=cfg.operator.value, value=cfg.value, action=action
        )

    raise ValueError(f"Unknown validator type: {cfg.type!r}")
