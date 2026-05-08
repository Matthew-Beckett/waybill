from typing import TYPE_CHECKING

from apps.channels.models import Stream

from .base import WaybillMatcherBase

if TYPE_CHECKING:
    from ..transformers.convert_cardinal_numbers import WaybillTransformerConvertCardinalNumbers
    from ..transformers.regex import WaybillTransformerRegex

    AnyTransformer = WaybillTransformerRegex | WaybillTransformerConvertCardinalNumbers


class WaybillMatcherHasPrefix(WaybillMatcherBase):
    def __init__(
        self,
        prefixes: list[str],
        field: str,
        action: str = "keep",
        case_sensitive: bool = False,
        pre_transformers: "list[AnyTransformer] | None" = None,
    ):
        super().__init__(field=field, action=action, case_sensitive=case_sensitive, pre_transformers=pre_transformers)
        if case_sensitive:
            self._prefixes = prefixes
        else:
            self._prefixes = [p.lower() for p in prefixes]

    def match(self, stream: Stream) -> bool:
        field_value = self._get_field_value(stream)
        if not self.case_sensitive:
            field_value = field_value.lower()
        has_prefix = any(field_value.startswith(p) for p in self._prefixes)
        # "keep" → True when condition is met; "drop" → True when condition is NOT met
        return not has_prefix if self.action == "drop" else has_prefix
