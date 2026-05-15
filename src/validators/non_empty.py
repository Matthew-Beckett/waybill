from apps.channels.models import Stream

from .base import WaybillChannelValidatorBase, WaybillStreamValidatorBase


class WaybillValidatorNonEmpty(WaybillStreamValidatorBase):
    """Asserts that a stream field is non-empty after transformation."""

    def validate(self, stream: Stream) -> bool:
        return bool(self._get_field_value(stream))

    def _describe_self(self) -> str:
        return f'nonEmpty(field="{self.field}")'


class WaybillValidatorNonEmptyChannel(WaybillChannelValidatorBase):
    """Asserts that an assembled channel field is non-empty."""

    def validate(self, channel) -> bool:
        return bool(self._get_field_value(channel))

    def _describe_self(self) -> str:
        return f'nonEmpty(scope="channel", field="{self.field}")'
