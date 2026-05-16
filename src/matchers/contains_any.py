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
        super().__init__(
            field=field,
            action=action,
            case_sensitive=case_sensitive,
            pre_transformers=pre_transformers,
        )
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

    def match_and_capture(
        self, stream: Stream, variables: "dict[str, str] | None" = None
    ) -> "tuple[bool, dict[str, str]]":
        """Match the stream after rendering each substring as a Jinja2 template.

        Template expressions in substring values are rendered using *variables*,
        allowing substring patterns to reference predefined pipeline variables.
        """
        variables_ctx: dict[str, str] = variables if variables is not None else {}
        rendered_substrings = [
            self._render_value(s, variables_ctx) for s in self._display_substrings
        ]
        field_value = self._get_field_value(stream, variables=variables_ctx)
        if not self.case_sensitive:
            field_value_cmp = field_value.lower()
            rendered_substrings = [s.lower() for s in rendered_substrings]
        else:
            field_value_cmp = field_value
        contains = any(s in field_value_cmp for s in rendered_substrings)
        matched = not contains if self.action == "drop" else contains
        return matched, {}
