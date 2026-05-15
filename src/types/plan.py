from __future__ import annotations

from dataclasses import dataclass, field

from .config import OrderStreamsBy


def _empty_stream_records() -> list["StreamRecord"]:
    return []


def _empty_channel_plans() -> list["ChannelPlan"]:
    return []


def _empty_member_plans() -> list["MemberPlan"]:
    return []


def _empty_group_plans() -> list["GroupPlan"]:
    return []


def _empty_profile_plans() -> list["ProfilePlan"]:
    return []


def _empty_transform_steps() -> list["TransformStep"]:
    return []


def _empty_dropped_records() -> list["DroppedRecord"]:
    return []


def _empty_str_list() -> list[str]:
    return []


def _empty_violations() -> list["ValidatorViolation"]:
    return []


@dataclass(frozen=True)
class TransformStep:
    """Records the effect of a single transformer step on a stream name."""

    transformer_index: int
    transformer_desc: str
    name_in: str
    name_out: str | None  # None means the stream was dropped at this step


@dataclass(frozen=True)
class DroppedRecord:
    """A stream that was dropped during transformation, with full step history."""

    original_name: str
    steps: list[TransformStep] = field(default_factory=_empty_transform_steps)


@dataclass(frozen=True)
class ValidatorViolation:
    """A single validator assertion that was not satisfied."""

    validator_index: int  # 1-based index into the member's validators list
    validator_desc: str
    action: str  # "warn" or "fail"
    scope: str  # "stream" or "channel"
    target: str  # transformed stream name or channel name


@dataclass(frozen=True)
class StreamRecord:
    id: int
    original_name: str
    transformed_name: str
    tvg_id: str | None = None
    logo_url: str | None = None
    order_reason: str | None = None
    steps: list[TransformStep] = field(default_factory=_empty_transform_steps)


@dataclass(frozen=True)
class ChannelPlan:
    """A single output channel, grouping one or more simulcast streams by their normalized name."""

    name: str
    epg_id: str | None = None
    logo_url: str | None = None
    stream_profile: str | None = None
    order_streams_by: OrderStreamsBy | None = None
    streams: list[StreamRecord] = field(default_factory=_empty_stream_records)


@dataclass(frozen=True)
class MemberPlan:
    """Result of processing a single ConfigMember — one per manifest member entry."""

    member_name: str
    matcher_descs: list[str] = field(default_factory=_empty_str_list)
    transformer_descs: list[str] = field(default_factory=_empty_str_list)
    validator_descs: list[str] = field(default_factory=_empty_str_list)
    channels: list[ChannelPlan] = field(default_factory=_empty_channel_plans)
    dropped: list[DroppedRecord] = field(default_factory=_empty_dropped_records)
    violations: list[ValidatorViolation] = field(default_factory=_empty_violations)

    @property
    def dropped_count(self) -> int:
        return len(self.dropped)


@dataclass(frozen=True)
class GroupPlan:
    """Result of processing a ConfigGroup — maps to a Dispatcharr ChannelGroup."""

    key: str
    name: str
    members: list[MemberPlan] = field(default_factory=_empty_member_plans)


@dataclass(frozen=True)
class ProfilePlan:
    key: str
    name: str = ""
    groups: list[GroupPlan] = field(default_factory=_empty_group_plans)


@dataclass(frozen=True)
class WaybillPlan:
    manifest_name: str
    profiles: list[ProfilePlan] = field(default_factory=_empty_profile_plans)

    def has_failures(self) -> bool:
        """Return True if any violation across all members has action == 'fail'."""
        return any(
            v.action == "fail"
            for profile in self.profiles
            for group in profile.groups
            for member in group.members
            for v in member.violations
        )
