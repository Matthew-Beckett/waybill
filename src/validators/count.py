import operator as _op
from typing import TYPE_CHECKING

from .base import WaybillChannelValidatorBase

if TYPE_CHECKING:
    from ..types.plan import StreamRecord

_OPERATORS = {
    "gt": _op.gt,
    "gte": _op.ge,
    "lt": _op.lt,
    "lte": _op.le,
    "eq": _op.eq,
    "neq": _op.ne,
}

_OPERATOR_SYMBOLS = {
    "gt": ">",
    "gte": ">=",
    "lt": "<",
    "lte": "<=",
    "eq": "==",
    "neq": "!=",
}


class WaybillValidatorCount(WaybillChannelValidatorBase):
    """Asserts that the number of streams in a channel satisfies a numeric comparison."""

    def __init__(self, operator: str, value: int, action: str = "warn") -> None:
        super().__init__(action=action)
        self._operator_key = operator
        self._compare = _OPERATORS[operator]
        self._value = value

    def validate(self, channel_name: str, streams: "list[StreamRecord]") -> bool:
        return self._compare(len(streams), self._value)

    def _describe_self(self) -> str:
        symbol = _OPERATOR_SYMBOLS.get(self._operator_key, self._operator_key)
        return f"count {symbol} {self._value}"
