from apps.channels.models import Stream

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
        value = getattr(stream, self.field)
        if self.prefix and value.startswith(self.prefix):
            value = value[len(self.prefix) :]
        if self.suffix and value.endswith(self.suffix):
            value = value[: -len(self.suffix)]
        setattr(stream, self.field, value)
        return stream

    def _describe_self(self) -> str:
        parts: list[str] = []
        if self.prefix:
            parts.append(f'prefix="{self.prefix}"')
        if self.suffix:
            parts.append(f'suffix="{self.suffix}"')
        field_note = f' on "{self.field}"' if self.field != "name" else ""
        return f"strip({(', ').join(parts)}){field_note}"
