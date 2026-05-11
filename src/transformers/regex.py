import re

from apps.channels.models import Stream

from .base import WaybillTransformerBase

# Convert $1-style backreferences to Python's \1 style.
_BACKREF_PATTERN = re.compile(r"\$(\d+)")


class WaybillTransformerRegex(WaybillTransformerBase):
    def __init__(self, pattern: str, action: str, replacement: str = "", field: str = "name"):
        self.pattern = pattern
        self.action = action
        self.replacement = _BACKREF_PATTERN.sub(r"\\\1", replacement)
        self.field = field

    def transform(self, stream: Stream) -> Stream | None:
        match self.action:
            case "drop":
                return None if re.search(self.pattern, getattr(stream, self.field)) else stream
            case "replace":
                setattr(stream, self.field, re.sub(self.pattern, self.replacement, getattr(stream, self.field)))
                return stream
            case _:
                raise ValueError(f"Unknown regex action: {self.action!r}")

    def _describe_self(self) -> str:
        field_note = f' on "{self.field}"' if self.field != "name" else ""
        match self.action:
            case "replace":
                return f'regex "{self.pattern}" \u2192 "{self.replacement}"{field_note}'
            case _:
                return f'regex "{self.pattern}" \u2192 {self.action}{field_note}'
