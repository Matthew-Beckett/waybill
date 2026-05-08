from apps.channels.models import Stream


class WaybillTransformerSet:
    """Sets a stream field to a fixed value, normalising all matched streams to a canonical name."""

    def __init__(self, value: str, field: str = "name"):
        self.field = field
        self.value = value

    def transform(self, stream: Stream) -> Stream | None:
        setattr(stream, self.field, self.value)
        return stream
