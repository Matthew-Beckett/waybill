from ..types.config import ConfigTransformer, TransformerType
from .convert_cardinal_numbers import WaybillTransformerConvertCardinalNumbers
from .regex import WaybillTransformerRegex
from .set import WaybillTransformerSet
from .strip import WaybillTransformerStrip

AnyTransformer = (
    WaybillTransformerRegex
    | WaybillTransformerConvertCardinalNumbers
    | WaybillTransformerStrip
    | WaybillTransformerSet
)


def build_transformer(cfg: ConfigTransformer) -> AnyTransformer:
    """Instantiate the concrete transformer for a ConfigTransformer."""
    if cfg.type == TransformerType.REGEX:
        return WaybillTransformerRegex(pattern=cfg.pattern, action=cfg.action, replacement=cfg.replacement)

    if cfg.type == TransformerType.CONVERT_CARDINAL_NUMBERS:
        direction = cfg.direction.value if hasattr(cfg.direction, "value") else str(cfg.direction)
        output_type = cfg.output_type.value if hasattr(cfg.output_type, "value") else str(cfg.output_type)
        return WaybillTransformerConvertCardinalNumbers(
            direction=direction,
            output_type=output_type,
            field=cfg.field,
        )

    if cfg.type == TransformerType.STRIP:
        return WaybillTransformerStrip(field=cfg.field, prefix=cfg.prefix, suffix=cfg.suffix)

    if cfg.type == TransformerType.SET:
        return WaybillTransformerSet(value=cfg.value, field=cfg.field)

    raise ValueError(f"Unknown transformer type: {cfg.type!r}")
