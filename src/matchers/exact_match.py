from apps.channels.models import Stream

from .base import WaybillMatcherBase


class WaybillMatcherExactMatch(WaybillMatcherBase):
    """Matches streams whose field value exactly equals one of the given values."""

    def __init__(
        self,
        values: list[str],
        field: str,
        action: str = "keep",
        case_sensitive: bool = False,
        pre_transformers=None,
    ):
        super().__init__(field=field, action=action, case_sensitive=case_sensitive, pre_transformers=pre_transformers)
        self._display_values = values
        if case_sensitive:
            self._values: set[str] = set(values)
        else:
            self._values = {v.lower() for v in values}

    def _describe_self(self) -> str:
        values = ", ".join(f'"{v}"' for v in self._display_values)
        cs = " (case-sensitive)" if self.case_sensitive else ""
        return f'exactMatch([{values}]) on "{self.field}"{cs}'

    def match(self, stream: Stream) -> bool:
        field_value = self._get_field_value(stream)
        if not self.case_sensitive:
            field_value = field_value.lower()
        matched = field_value in self._values
        return not matched if self.action == "drop" else matched
