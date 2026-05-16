from apps.channels.models import Stream

from .base import WaybillTransformerBase


class WaybillTransformerSet(WaybillTransformerBase):
    """Sets a stream field to a fixed value, normalising all matched streams to a canonical name."""

    def __init__(self, value: str, field: str = "name"):
        self.field = field
        self.value = value

    def transform(
        self, stream: Stream, variables: "dict[str, str] | None" = None
    ) -> "Stream | None":
        setattr(stream, self.field, self.value)
        return stream

    def _describe_self(self) -> str:
        return f'set \u2192 "{self.value}" on {self.field}'
