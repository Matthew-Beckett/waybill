from __future__ import annotations

import jinja2

from apps.channels.models import Stream

from .base import WaybillTransformerBase


_JINJA_ENV = jinja2.Environment(
    undefined=jinja2.StrictUndefined,
    autoescape=False,
)


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
        self._template = _JINJA_ENV.from_string(value)

    def transform(
        self, stream: Stream, variables: "dict[str, str] | None" = None
    ) -> "Stream | None":
        ctx: dict[str, str] = variables if variables is not None else {}
        rendered = self._template.render(**ctx)
        setattr(stream, self.field, rendered)
        return stream

    def _describe_self(self) -> str:
        field_note = f' on "{self.field}"' if self.field != "name" else ""
        return f'template \u2192 "{self._raw_value}"{field_note}'
