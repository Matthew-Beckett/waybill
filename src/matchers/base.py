from copy import copy
from typing import TYPE_CHECKING

from apps.channels.models import Stream

if TYPE_CHECKING:
    from ..transformers.convert_cardinal_numbers import WaybillTransformerConvertCardinalNumbers
    from ..transformers.regex import WaybillTransformerRegex

    AnyTransformer = WaybillTransformerRegex | WaybillTransformerConvertCardinalNumbers


class WaybillMatcherBase:
    """Base class for all Waybill matchers.

    Provides common fields (field, action, case_sensitive, pre_transformers) and
    a helper to apply pre-transformers before reading the field value.
    """

    def __init__(
        self,
        field: str,
        action: str = "keep",
        case_sensitive: bool = False,
        pre_transformers: "list[AnyTransformer] | None" = None,
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

    def match(self, stream: Stream) -> bool:
        raise NotImplementedError
