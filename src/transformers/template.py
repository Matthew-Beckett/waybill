from __future__ import annotations

from apps.channels.models import Stream

from .._jinja import render_template
from .base import WaybillTransformerBase


class WaybillTransformerTemplate(WaybillTransformerBase):
    """Renders a Jinja2 template string using per-stream capture variables.

    The ``value`` field is a Jinja2 template (e.g. ``"{{ ch_name }} ({{ quality }})"``).
    Variables are supplied by named capture groups from preceding regex matchers and
    by any predefined pipeline variables.  Uses ``StrictUndefined`` so that
    referencing an undefined variable raises an error rather than silently
    producing an empty string.  All standard Jinja2 filters are available.
    """

    def __init__(self, value: str, field: str = "name") -> None:
        self.field = field
        self._raw_value = value

    def transform(
        self, stream: Stream, variables: "dict[str, str] | None" = None
    ) -> "Stream | None":
        ctx: dict[str, str] = variables if variables is not None else {}
        rendered = render_template(
            self._raw_value,
            ctx,
            context_desc=f'template transformer "{self.field}" field',
        )
        setattr(stream, self.field, rendered)
        return stream

    def template_field_strings(self) -> "list[tuple[str, str]]":
        return [(f'template transformer "{self.field}" field', self._raw_value)]

    def _describe_self(self) -> str:
        field_note = f' on "{self.field}"' if self.field != "name" else ""
        return f'template \u2192 "{self._raw_value}"{field_note}'
