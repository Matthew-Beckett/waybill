from apps.channels.models import Stream

from .base import WaybillMatcherBase


class WaybillMatcherContainsAny(WaybillMatcherBase):
    """Matches streams whose field value contains at least one of the given substrings."""

    def __init__(
        self,
        substrings: list[str],
        field: str,
        action: str = "keep",
        case_sensitive: bool = False,
        pre_transformers=None,
    ):
        super().__init__(field=field, action=action, case_sensitive=case_sensitive, pre_transformers=pre_transformers)
        self._display_substrings = substrings
        if case_sensitive:
            self._substrings = substrings
        else:
            self._substrings = [s.lower() for s in substrings]

    def _describe_self(self) -> str:
        substrings = ", ".join(f'"{s}"' for s in self._display_substrings)
        cs = " (case-sensitive)" if self.case_sensitive else ""
        return f'containsAny([{substrings}]) on "{self.field}"{cs}'

    def match(self, stream: Stream) -> bool:
        field_value = self._get_field_value(stream)
        if not self.case_sensitive:
            field_value = field_value.lower()
        contains = any(s in field_value for s in self._substrings)
        return not contains if self.action == "drop" else contains
