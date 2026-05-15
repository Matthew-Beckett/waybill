import operator as _op
from collections.abc import Callable
from typing import TYPE_CHECKING

from .base import WaybillChannelValidatorBase, WaybillMemberValidatorBase

if TYPE_CHECKING:
    from ..types.plan import ChannelPlan, MemberPlan

_OPERATORS: dict[str, Callable[[int, int], bool]] = {
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


class WaybillValidatorCountChannel(WaybillChannelValidatorBase):
    """Asserts that the number of streams in a channel satisfies a numeric comparison."""

    def __init__(self, operator: str, value: int, action: str = "warn") -> None:
        super().__init__(action=action)
        self._operator_key = operator
        self._compare = _OPERATORS[operator]
        self._value = value

    def validate(self, channel: "ChannelPlan") -> bool:
        return self._compare(len(channel.streams), self._value)

    def _describe_self(self) -> str:
        symbol = _OPERATOR_SYMBOLS.get(self._operator_key, self._operator_key)
        return f'count(scope="channel") {symbol} {self._value}'


class WaybillValidatorCountMember(WaybillMemberValidatorBase):
    """Asserts that the number of channels in a member satisfies a numeric comparison."""

    def __init__(self, operator: str, value: int, action: str = "warn") -> None:
        super().__init__(action=action)
        self._operator_key = operator
        self._compare = _OPERATORS[operator]
        self._value = value

    def validate(self, member_plan: "MemberPlan") -> bool:
        return self._compare(len(member_plan.channels), self._value)

    def _describe_self(self) -> str:
        symbol = _OPERATOR_SYMBOLS.get(self._operator_key, self._operator_key)
        return f'count(scope="member") {symbol} {self._value}'
