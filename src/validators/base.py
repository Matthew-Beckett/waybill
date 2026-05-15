from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from apps.channels.models import Stream

if TYPE_CHECKING:
    from ..types.plan import ChannelPlan, MemberPlan


class WaybillStreamValidatorBase(ABC):
    """Abstract base class for stream-level validators.

    A stream-level validator inspects a single transformed stream and returns
    True if the stream satisfies the assertion, False otherwise.
    """

    def __init__(self, action: str = "warn", field: str = "name") -> None:
        self.action = action
        self.field = field

    def _get_field_value(self, stream: Stream) -> str:
        """Return the stream field value as a string."""
        return str(getattr(stream, self.field, "") or "")

    @abstractmethod
    def validate(self, stream: Stream) -> bool:
        """Return True if the stream satisfies this assertion."""

    @abstractmethod
    def _describe_self(self) -> str:
        """Return a description of this validator's core logic."""

    def describe(self) -> str:
        return f"{self._describe_self()} → {self.action}"


class WaybillChannelValidatorBase(ABC):
    """Abstract base class for channel-level (aggregate) validators.

    A channel-level validator inspects a fully assembled ChannelPlan and
    returns True if the assertion is satisfied.
    """

    def __init__(self, action: str = "warn", field: str = "name") -> None:
        self.action = action
        self.field = field

    def _get_field_value(self, channel: "ChannelPlan") -> str:
        """Return the assembled channel field value as a string."""
        channel_field = "epg_id" if self.field == "tvg_id" else self.field
        return str(getattr(channel, channel_field, "") or "")

    @abstractmethod
    def validate(self, channel: "ChannelPlan") -> bool:
        """Return True if the channel satisfies this assertion."""

    @abstractmethod
    def _describe_self(self) -> str:
        """Return a description of this validator's core logic."""

    def describe(self) -> str:
        return f"{self._describe_self()} → {self.action}"


class WaybillMemberValidatorBase(ABC):
    """Abstract base class for member-level validators.

    A member-level validator inspects the full MemberPlan, including the case
    where the member produced zero channels.
    """

    def __init__(self, action: str = "warn") -> None:
        self.action = action

    @abstractmethod
    def validate(self, member_plan: "MemberPlan") -> bool:
        """Return True if the member satisfies this assertion."""

    @abstractmethod
    def _describe_self(self) -> str:
        """Return a description of this validator's core logic."""

    def describe(self) -> str:
        return f"{self._describe_self()} → {self.action}"
