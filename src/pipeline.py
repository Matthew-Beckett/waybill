from __future__ import annotations

from collections import defaultdict
from copy import copy
from dataclasses import replace

from apps.channels.models import Stream

from .matchers import build_matcher, build_q_filter
from .matchers.base import WaybillMatcherBase
from .transformers import build_transformer
from .validators import build_validator
from .validators.base import WaybillChannelValidatorBase, WaybillStreamValidatorBase
from .types.config import (
    ConfigMember,
    ConfigProfile,
    OrderStreamsBy,
    WaybillConfig,
)
from .plan import assemble_member_plan
from .types.plan import (
    GroupPlan,
    DroppedRecord,
    MemberPlan,
    ProfilePlan,
    StreamRecord,
    TransformStep,
    ValidatorViolation,
    WaybillPlan,
)

CHUNK_SIZE = 1000


class MemberPipeline:
    """Encapsulates matcher and transformer instances for a single ConfigMember."""

    def __init__(
        self,
        member: ConfigMember,
        inherited_stream_profile: "str | None" = None,
        inherited_order_streams_by: "OrderStreamsBy | None" = None,
    ) -> None:
        self._member = member
        self._effective_stream_profile: str | None = (
            member.stream_profile or inherited_stream_profile
        )
        self._effective_order_streams_by: OrderStreamsBy | None = (
            member.order_streams_by or inherited_order_streams_by
        )
        self._matchers: list[WaybillMatcherBase] = [
            build_matcher(cfg) for cfg in member.matchers
        ]
        self._transformers = [build_transformer(cfg) for cfg in member.transformers]
        # Fields actually needed by matchers and their pre-transformers — drives .only() to keep ORM objects lean
        self._required_fields: set[str] = (
            {cfg.field for cfg in member.matchers}
            | {t.field for cfg in member.matchers for t in cfg.transformers}
            | {"id", "name", "tvg_id", "logo_url"}
        )
        if self._effective_order_streams_by is OrderStreamsBy.QUALITY:
            self._required_fields.add("stream_stats")
        self._matcher_descs: list[str] = [m.describe() for m in self._matchers]
        self._transformer_descs: list[str] = [t.describe() for t in self._transformers]

        _all_validators = [build_validator(cfg) for cfg in member.validators]
        self._validator_descs: list[str] = [v.describe() for v in _all_validators]
        # Partition into stream-level and channel-level, preserving 1-based original indices
        self._stream_validator_pairs: list[
            tuple[WaybillStreamValidatorBase, str, int]
        ] = [
            (v, self._validator_descs[i], i + 1)
            for i, v in enumerate(_all_validators)
            if isinstance(v, WaybillStreamValidatorBase)
        ]
        self._channel_validator_pairs: list[
            tuple[WaybillChannelValidatorBase, str, int]
        ] = [
            (v, self._validator_descs[i], i + 1)
            for i, v in enumerate(_all_validators)
            if isinstance(v, WaybillChannelValidatorBase)
        ]

    def required_fields(self) -> set[str]:
        return self._required_fields

    def matches(self, stream: Stream) -> bool:
        """Return True only if ALL matchers accept the stream."""
        return all(m.match(stream) for m in self._matchers)

    def process(self, chunk_size: int = CHUNK_SIZE) -> MemberPlan:
        """
        Query, match, and transform streams for this member.

        Uses an ORM pre-filter (iregex) to reduce the result set before
        applying Python matchers for precise correctness. Streams are consumed
        via an iterator to avoid loading the full queryset into memory.
        Each transformer step is recorded for verbose plan output.
        """
        q_filter = build_q_filter(self._member.matchers)
        qs = (
            Stream.objects.filter(q_filter)
            .only(*self._required_fields)
            .iterator(chunk_size=chunk_size)
        )

        # Each group holds (stream_stats, StreamRecord); stream_stats is a raw dict captured
        # while the ORM object is still in scope and passed to the plan assembler.
        groups: defaultdict[str, list[tuple["dict | None", StreamRecord]]] = (
            defaultdict(list)
        )
        dropped_records: list[DroppedRecord] = []
        all_violations: list[ValidatorViolation] = []

        transformer_pairs = list(
            zip(
                self._transformers,
                self._transformer_descs,
                range(1, len(self._transformers) + 1),
            )
        )

        for stream in qs:
            # Precise Python match — guards against ORM iregex false positives
            if not self.matches(stream):
                continue

            original_name = stream.name
            # Work on a shallow copy so transformers can mutate .name freely
            working = copy(stream)
            steps: list[TransformStep] = []
            was_dropped = False

            for transformer, desc, idx in transformer_pairs:
                name_in = working.name
                result = transformer.transform(working)
                if result is None:
                    steps.append(
                        TransformStep(
                            transformer_index=idx,
                            transformer_desc=desc,
                            name_in=name_in,
                            name_out=None,
                        )
                    )
                    dropped_records.append(
                        DroppedRecord(original_name=original_name, steps=steps)
                    )
                    was_dropped = True
                    break
                steps.append(
                    TransformStep(
                        transformer_index=idx,
                        transformer_desc=desc,
                        name_in=name_in,
                        name_out=result.name,
                    )
                )
                working = result

            if not was_dropped:
                stream_stats = getattr(stream, "stream_stats", None)
                groups[working.name].append(
                    (
                        stream_stats,
                        StreamRecord(
                            id=stream.pk,
                            original_name=original_name,
                            transformed_name=working.name,
                            tvg_id=stream.tvg_id,
                            logo_url=stream.logo_url,
                            steps=steps,
                        ),
                    )
                )
                # Stream-level validators run after transformation; violations are observational
                for sv, desc, idx in self._stream_validator_pairs:
                    if not sv.validate(working):
                        all_violations.append(
                            ValidatorViolation(
                                validator_index=idx,
                                validator_desc=desc,
                                action=sv.action,
                                scope="stream",
                                target=working.name,
                            )
                        )

        member_plan = assemble_member_plan(
            member_name=self._member.name,
            matcher_descs=self._matcher_descs,
            transformer_descs=self._transformer_descs,
            raw_groups=groups,
            dropped=dropped_records,
            effective_stream_profile=self._effective_stream_profile,
            effective_order_streams_by=self._effective_order_streams_by,
        )

        # Channel-level validators run post-assembly against each assembled channel
        for cv, desc, idx in self._channel_validator_pairs:
            for channel in member_plan.channels:
                if not cv.validate(channel.name, channel.streams):
                    all_violations.append(
                        ValidatorViolation(
                            validator_index=idx,
                            validator_desc=desc,
                            action=cv.action,
                            scope="channel",
                            target=channel.name,
                        )
                    )

        return replace(
            member_plan,
            validator_descs=self._validator_descs,
            violations=all_violations,
        )


class GroupPipeline:
    """Encapsulates processing for a single ConfigGroup (→ Dispatcharr ChannelGroup)."""

    def __init__(
        self,
        key: str,
        name: str,
        members: list[ConfigMember],
        inherited_stream_profile: "str | None" = None,
        group_stream_profile: "str | None" = None,
        inherited_order_streams_by: "OrderStreamsBy | None" = None,
        group_order_streams_by: "OrderStreamsBy | None" = None,
    ) -> None:
        self._key = key
        self._name = name
        effective_sp = group_stream_profile or inherited_stream_profile
        effective_osb = group_order_streams_by or inherited_order_streams_by
        self._pipelines = [
            MemberPipeline(
                m,
                inherited_stream_profile=effective_sp,
                inherited_order_streams_by=effective_osb,
            )
            for m in members
        ]

    def process(self, chunk_size: int = CHUNK_SIZE) -> GroupPlan:
        return GroupPlan(
            key=self._key,
            name=self._name,
            members=[p.process(chunk_size=chunk_size) for p in self._pipelines],
        )


class ProfilePipeline:
    """Encapsulates processing for a single ConfigProfile."""

    def __init__(self, key: str, profile: ConfigProfile) -> None:
        self._key = key
        self._name = profile.name
        self._pipelines = [
            GroupPipeline(
                key=cat_key,
                name=cat.name,
                members=cat.members,
                inherited_stream_profile=profile.stream_profile,
                group_stream_profile=cat.stream_profile,
                inherited_order_streams_by=profile.order_streams_by,
                group_order_streams_by=cat.order_streams_by,
            )
            for cat_key, cat in profile.groups.items()
        ]

    def process(self, chunk_size: int = CHUNK_SIZE) -> ProfilePlan:
        return ProfilePlan(
            key=self._key,
            name=self._name,
            groups=[c.process(chunk_size=chunk_size) for c in self._pipelines],
        )


class WaybillPipeline:
    """Top-level pipeline that processes all profiles in the manifest."""

    def __init__(self, config: WaybillConfig) -> None:
        self._config = config
        self._profiles = [
            ProfilePipeline(key=prof_key, profile=prof)
            for prof_key, prof in config.spec.profiles.items()
        ]

    def compute_plan(self, chunk_size: int = CHUNK_SIZE) -> WaybillPlan:
        return WaybillPlan(
            manifest_name=self._config.metadata.name,
            profiles=[p.process(chunk_size=chunk_size) for p in self._profiles],
        )
