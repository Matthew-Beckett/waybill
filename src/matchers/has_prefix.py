from apps.channels.models import Stream

from .base import WaybillMatcherBase


class WaybillMatcherHasPrefix(WaybillMatcherBase):
    def __init__(
        self,
        prefixes: list[str],
        field: str,
        action: str = "keep",
        case_sensitive: bool = False,
        pre_transformers=None,
    ):
        super().__init__(field=field, action=action, case_sensitive=case_sensitive, pre_transformers=pre_transformers)
        self._display_prefixes = prefixes
        if case_sensitive:
            self._prefixes = prefixes
        else:
            self._prefixes = [p.lower() for p in prefixes]

    def _describe_self(self) -> str:
        prefixes = ", ".join(f'"{p}"' for p in self._display_prefixes)
        cs = " (case-sensitive)" if self.case_sensitive else ""
        return f'hasPrefix([{prefixes}]) on "{self.field}"{cs}'

    def match(self, stream: Stream) -> bool:
        field_value = self._get_field_value(stream)
        if not self.case_sensitive:
            field_value = field_value.lower()
        has_prefix = any(field_value.startswith(p) for p in self._prefixes)
        # "keep" → True when condition is met; "drop" → True when condition is NOT met
        return not has_prefix if self.action == "drop" else has_prefix
