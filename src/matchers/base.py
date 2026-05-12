from abc import ABC, abstractmethod
from copy import copy
from typing import TYPE_CHECKING

from apps.channels.models import Stream

if TYPE_CHECKING:
    from ..transformers.base import WaybillTransformerBase


class WaybillMatcherBase(ABC):
    """Abstract base class for all Waybill matchers.

    Provides common fields (field, action, case_sensitive, pre_transformers) and
    a helper to apply pre-transformers before reading the field value.
    Subclasses implement _describe_self() and get describe() for free.
    """

    def __init__(
        self,
        field: str,
        action: str = "keep",
        case_sensitive: bool = False,
        pre_transformers: "list[WaybillTransformerBase] | None" = None,
    ):
        self.field = field
        self.action = action
        self.case_sensitive = case_sensitive
        self.pre_transformers: list = pre_transformers or []

    def _get_field_value(self, stream: Stream) -> str:
        """Return the field value after applying any pre-transformers."""
        if self.pre_transformers:
            working = copy(stream)
            for t in self.pre_transformers:
                result = t.transform(working)
                if result is not None:
                    working = result
            return getattr(working, self.field)
        return getattr(stream, self.field)

    @abstractmethod
    def _describe_self(self) -> str:
        """Return a description of this matcher's core logic (without action or pre-transformer decoration)."""

    @abstractmethod
    def match(self, stream: Stream) -> bool:
        """Return True if this matcher accepts the stream."""

    def describe(self) -> str:
        """Return a human-readable description of this matcher, including action and pre-transformers."""
        suffix = (
            f" \u2192 {self.action}" if self.action and self.action != "keep" else ""
        )
        desc = f"{self._describe_self()}{suffix}"
        if self.pre_transformers:
            pre_descs = "; ".join(t.describe() for t in self.pre_transformers)
            desc = f"[pre: {pre_descs}] {desc}"
        return desc
