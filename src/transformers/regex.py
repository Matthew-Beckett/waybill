import re

from apps.channels.models import Stream

from .._jinja import render_template
from .base import WaybillTransformerBase

# Convert $1-style backreferences to Python's \1 style.
# Applied at __init__ time on the raw replacement string before it is stored
# as a Jinja2 template.  This means template expressions ({{ var }}) in the
# replacement are rendered *after* backreference conversion, so $N and
# {{ var }} can coexist safely (e.g. ``"\1 {{ suffix }}"``).
_BACKREF_PATTERN = re.compile(r"\$(\d+)")


class WaybillTransformerRegex(WaybillTransformerBase):
    def __init__(
        self, pattern: str, action: str, replacement: str = "", field: str = "name"
    ):
        self.pattern = pattern
        self.action = action
        self.replacement = _BACKREF_PATTERN.sub(r"\\\1", replacement)
        self.field = field

    def transform(
        self, stream: Stream, variables: "dict[str, str] | None" = None
    ) -> "Stream | None":
        ctx: dict[str, str] = variables if variables is not None else {}
        pattern = render_template(
            self.pattern, ctx, context_desc="regex transformer pattern field"
        )
        replacement = render_template(
            self.replacement, ctx, context_desc="regex transformer replacement field"
        )
        match self.action:
            case "drop":
                return (
                    None if re.search(pattern, getattr(stream, self.field)) else stream
                )
            case "replace":
                setattr(
                    stream,
                    self.field,
                    re.sub(pattern, replacement, getattr(stream, self.field)),
                )
                return stream
            case _:
                raise ValueError(f"Unknown regex action: {self.action!r}")

    def template_field_strings(self) -> "list[tuple[str, str]]":
        pairs: list[tuple[str, str]] = [
            ("regex transformer pattern field", self.pattern),
        ]
        if self.replacement:
            pairs.append(("regex transformer replacement field", self.replacement))
        return pairs

    def _describe_self(self) -> str:
        field_note = f' on "{self.field}"' if self.field != "name" else ""
        match self.action:
            case "replace":
                return f'regex "{self.pattern}" \u2192 "{self.replacement}"{field_note}'
            case _:
                return f'regex "{self.pattern}" \u2192 {self.action}{field_note}'
