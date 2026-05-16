from apps.channels.models import Stream

from .._jinja import render_template
from .base import WaybillTransformerBase


class WaybillTransformerSetMetadata(WaybillTransformerBase):
    """Sets explicit stream metadata fields to fixed values."""

    def __init__(
        self,
        name: str = "",
        logo_url: str = "",
        tvg_id: str = "",
    ):
        self.name = name
        self.logo_url = logo_url
        self.tvg_id = tvg_id

        if not any((self.name, self.logo_url, self.tvg_id)):
            raise ValueError("setMetadata requires at least one metadata field")

    def transform(
        self, stream: Stream, variables: "dict[str, str] | None" = None
    ) -> "Stream | None":
        ctx: dict[str, str] = variables if variables is not None else {}
        if self.name:
            stream.name = render_template(
                self.name, ctx, context_desc="setMetadata transformer name field"
            )
        if self.logo_url:
            stream.logo_url = render_template(
                self.logo_url, ctx, context_desc="setMetadata transformer logoUrl field"
            )
        if self.tvg_id:
            stream.tvg_id = render_template(
                self.tvg_id, ctx, context_desc="setMetadata transformer tvgId field"
            )
        return stream

    def template_field_strings(self) -> "list[tuple[str, str]]":
        pairs: list[tuple[str, str]] = []
        if self.name:
            pairs.append(("setMetadata transformer name field", self.name))
        if self.logo_url:
            pairs.append(("setMetadata transformer logoUrl field", self.logo_url))
        if self.tvg_id:
            pairs.append(("setMetadata transformer tvgId field", self.tvg_id))
        return pairs

    def _describe_self(self) -> str:
        assignments = []
        if self.name:
            assignments.append(f'name="{self.name}"')
        if self.logo_url:
            assignments.append(f'logoUrl="{self.logo_url}"')
        if self.tvg_id:
            assignments.append(f'tvgId="{self.tvg_id}"')

        return "setMetadata -> " + ", ".join(assignments)
