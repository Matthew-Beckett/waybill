from apps.channels.models import Stream


class WaybillTransformerStrip:
    """Strips a fixed prefix and/or suffix from a stream field."""

    def __init__(self, field: str = "name", prefix: str = "", suffix: str = ""):
        self.field = field
        self.prefix = prefix
        self.suffix = suffix

    def transform(self, stream: Stream) -> Stream | None:
        value = getattr(stream, self.field)
        if self.prefix and value.startswith(self.prefix):
            value = value[len(self.prefix):]
        if self.suffix and value.endswith(self.suffix):
            value = value[: -len(self.suffix)]
        setattr(stream, self.field, value)
        return stream
