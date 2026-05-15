from apps.channels.models import Stream

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

    def transform(self, stream: Stream) -> Stream | None:
        if self.name:
            stream.name = self.name
        if self.logo_url:
            stream.logo_url = self.logo_url
        if self.tvg_id:
            stream.tvg_id = self.tvg_id
        return stream

    def _describe_self(self) -> str:
        assignments = []
        if self.name:
            assignments.append(f'name="{self.name}"')
        if self.logo_url:
            assignments.append(f'logoUrl="{self.logo_url}"')
        if self.tvg_id:
            assignments.append(f'tvgId="{self.tvg_id}"')

        return "setMetadata -> " + ", ".join(assignments)
