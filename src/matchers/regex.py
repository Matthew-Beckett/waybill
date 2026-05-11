import re

from apps.channels.models import Stream

from .base import WaybillMatcherBase


class WaybillMatcherRegex(WaybillMatcherBase):
    def __init__(
        self,
        pattern: str,
        field: str,
        action: str = "keep",
        case_sensitive: bool = False,
        pre_transformers=None,
    ):
        super().__init__(field=field, action=action, case_sensitive=case_sensitive, pre_transformers=pre_transformers)
        self.pattern = pattern

    def _describe_self(self) -> str:
        return f'regex on "{self.field}": {self.pattern}'

    def match(self, stream: Stream) -> bool:
        field_value = self._get_field_value(stream)
        flags = 0 if self.case_sensitive else re.IGNORECASE
        matched = bool(re.match(self.pattern, field_value, flags))
        return not matched if self.action == "drop" else matched