from typing import TYPE_CHECKING

from apps.channels.models import Stream

from .base import WaybillMatcherBase

if TYPE_CHECKING:
    from ..transformers.convert_cardinal_numbers import WaybillTransformerConvertCardinalNumbers
    from ..transformers.regex import WaybillTransformerRegex

    AnyTransformer = WaybillTransformerRegex | WaybillTransformerConvertCardinalNumbers


class WaybillMatcherExactMatch(WaybillMatcherBase):
    """Matches streams whose field value exactly equals one of the given values."""

    def __init__(
        self,
        values: list[str],
        field: str,
        action: str = "keep",
        case_sensitive: bool = False,
        pre_transformers: "list[AnyTransformer] | None" = None,
    ):
        super().__init__(field=field, action=action, case_sensitive=case_sensitive, pre_transformers=pre_transformers)
        if case_sensitive:
            self._values: set[str] = set(values)
        else:
            self._values = {v.lower() for v in values}

    def match(self, stream: Stream) -> bool:
        field_value = self._get_field_value(stream)
        if not self.case_sensitive:
            field_value = field_value.lower()
        matched = field_value in self._values
        return not matched if self.action == "drop" else matched
