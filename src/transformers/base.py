from abc import ABC, abstractmethod

from apps.channels.models import Stream


class WaybillTransformerBase(ABC):
    """Abstract base class for all Waybill transformers.

    Subclasses implement _describe_self() and get describe() for free.
    """

    @abstractmethod
    def transform(
        self, stream: Stream, variables: "dict[str, str] | None" = None
    ) -> "Stream | None":
        """Apply the transformation. Return None to drop the stream."""

    @abstractmethod
    def _describe_self(self) -> str:
        """Return a description of this transformer's core logic."""

    def describe(self) -> str:
        """Return a human-readable description of this transformer."""
        return self._describe_self()
