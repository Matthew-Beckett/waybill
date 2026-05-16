from apps.channels.models import Stream

from .._jinja import render_template
from .base import WaybillTransformerBase


class WaybillTransformerStrip(WaybillTransformerBase):
    """Strips a fixed prefix and/or suffix from a stream field."""

    def __init__(self, field: str = "name", prefix: str = "", suffix: str = ""):
        self.field = field
        self.prefix = prefix
        self.suffix = suffix

    def transform(
        self, stream: Stream, variables: "dict[str, str] | None" = None
    ) -> "Stream | None":
        ctx: dict[str, str] = variables if variables is not None else {}
        prefix = (
            render_template(
                self.prefix, ctx, context_desc="strip transformer prefix field"
            )
            if self.prefix
            else ""
        )
        suffix = (
            render_template(
                self.suffix, ctx, context_desc="strip transformer suffix field"
            )
            if self.suffix
            else ""
        )
        value = getattr(stream, self.field)
        if prefix and value.startswith(prefix):
            value = value[len(prefix) :]
        if suffix and value.endswith(suffix):
            value = value[: -len(suffix)]
        setattr(stream, self.field, value)
        return stream

    def template_field_strings(self) -> "list[tuple[str, str]]":
        pairs: list[tuple[str, str]] = []
        if self.prefix:
            pairs.append(("strip transformer prefix field", self.prefix))
        if self.suffix:
            pairs.append(("strip transformer suffix field", self.suffix))
        return pairs

    def _describe_self(self) -> str:
        parts: list[str] = []
        if self.prefix:
            parts.append(f'prefix="{self.prefix}"')
        if self.suffix:
            parts.append(f'suffix="{self.suffix}"')
        field_note = f' on "{self.field}"' if self.field != "name" else ""
        return f"strip({(', ').join(parts)}){field_note}"
