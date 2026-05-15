import re

from apps.channels.models import Stream

from .base import WaybillStreamValidatorBase


class WaybillValidatorRegexMatch(WaybillStreamValidatorBase):
    """Asserts that a stream field matches a regular expression after transformation."""

    def __init__(self, pattern: str, action: str = "warn", field: str = "name") -> None:
        super().__init__(action=action, field=field)
        self._pattern = pattern
        self._compiled = re.compile(pattern)

    def validate(self, stream: Stream) -> bool:
        return bool(self._compiled.search(self._get_field_value(stream)))

    def _describe_self(self) -> str:
        return f'regexMatch(pattern="{self._pattern}", field="{self.field}")'
