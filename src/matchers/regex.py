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
        super().__init__(
            field=field,
            action=action,
            case_sensitive=case_sensitive,
            pre_transformers=pre_transformers,
        )
        self.pattern = pattern

    def _describe_self(self) -> str:
        named_groups = re.findall(r"\(\?P<(\w+)>", self.pattern)
        captures_note = (
            f" [captures: {', '.join(named_groups)}]" if named_groups else ""
        )
        return f'regex on "{self.field}": {self.pattern}{captures_note}'

    def match(self, stream: Stream) -> bool:
        field_value = self._get_field_value(stream)
        flags = 0 if self.case_sensitive else re.IGNORECASE
        matched = bool(re.match(self.pattern, field_value, flags))
        return not matched if self.action == "drop" else matched

    def match_and_capture(
        self, stream: Stream, variables: "dict[str, str] | None" = None
    ) -> "tuple[bool, dict[str, str]]":
        """Match the stream and return ``(matched, named_captures)``.

        Named capture groups (``(?P<name>...)``) from a successful regex match
        are returned as a dict.  For a ``drop`` action, a matched stream is
        *rejected* (returns ``False``) with no captures; an unmatched stream
        is *accepted* (returns ``True``) with no captures.
        """
        field_value = self._get_field_value(stream, variables=variables)
        flags = 0 if self.case_sensitive else re.IGNORECASE
        m = re.match(self.pattern, field_value, flags)

        if self.action == "drop":
            # Matched → stream is dropped; unmatched → stream is kept (no captures)
            return (False, {}) if m else (True, {})

        # keep (default)
        if m:
            return True, {k: v for k, v in m.groupdict().items() if v is not None}
        return False, {}
