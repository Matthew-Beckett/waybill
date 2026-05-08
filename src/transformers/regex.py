import re

from apps.channels.models import Stream

# Convert $1-style backreferences to Python's \1 style.
_BACKREF_PATTERN = re.compile(r"\$(\d+)")


class WaybillTransformerRegex:
    def __init__(self, pattern: str, action: str, replacement: str = ""):
        self.type = "regex"
        self.pattern = pattern
        self.action = action
        self.replacement = _BACKREF_PATTERN.sub(r"\\\1", replacement)

    def transform(self, stream: Stream) -> Stream | None:
        if self.action == "drop":
            return None if re.search(self.pattern, stream.name) else stream
        if self.action == "replace":
            stream.name = re.sub(self.pattern, self.replacement, stream.name)
            return stream
        raise ValueError(f"Unknown regex action: {self.action!r}")

    def apply(self, streams: list[Stream]) -> list[Stream]:
        result = []
        for stream in streams:
            transformed = self.transform(stream)
            if transformed is not None:
                result.append(transformed)
        return result
