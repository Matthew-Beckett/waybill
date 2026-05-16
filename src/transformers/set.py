from apps.channels.models import Stream

from .._jinja import render_template
from .base import WaybillTransformerBase


class WaybillTransformerSet(WaybillTransformerBase):
    """Sets a stream field to a fixed value, normalising all matched streams to a canonical name."""

    def __init__(self, value: str, field: str = "name"):
        self.field = field
        self.value = value

    def transform(
        self, stream: Stream, variables: "dict[str, str] | None" = None
    ) -> "Stream | None":
        ctx: dict[str, str] = variables if variables is not None else {}
        rendered = render_template(
            self.value, ctx, context_desc=f'set transformer "{self.field}" field'
        )
        setattr(stream, self.field, rendered)
        return stream

    def template_field_strings(self) -> "list[tuple[str, str]]":
        return [(f'set transformer "{self.field}" field', self.value)]

    def _describe_self(self) -> str:
        return f'set \u2192 "{self.value}" on {self.field}'
