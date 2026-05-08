from __future__ import annotations

from collections import Counter, defaultdict
from copy import copy
from typing import TYPE_CHECKING, Iterable

from apps.channels.models import Stream

from .matchers import build_matcher, build_q_filter
from .transformers import build_transformer
from .types.config import (
    ConfigMatcher,
    ConfigMember,
    ConfigProfile,
    ConfigTransformer,
    MatcherAction,
    MatcherType,
    TransformerType,
    WaybillConfig,
)
from .types.plan import (
    GroupPlan,
    ChannelPlan,
    DroppedRecord,
    MemberPlan,
    ProfilePlan,
    StreamRecord,
    TransformStep,
    WaybillPlan,
)

if TYPE_CHECKING:
    from .matchers.has_prefix import WaybillMatcherHasPrefix
    from .matchers.regex import WaybillMatcherRegex
    from .matchers.contains_any import WaybillMatcherContainsAny
    from .matchers.exact_match import WaybillMatcherExactMatch

CHUNK_SIZE = 1000


def _most_common(values: "Iterable[str | None]") -> "str | None":
    """Return the most frequently occurring non-None value, or None if all are absent."""
    counts: Counter[str] = Counter(v for v in values if v)
    if not counts:
        return None
    return counts.most_common(1)[0][0]


def _describe_matcher(cfg: ConfigMatcher) -> str:
    action = cfg.action.value if isinstance(cfg.action, MatcherAction) else str(cfg.action)
    suffix = f" \u2192 {action}" if action and action != "keep" else ""
    if cfg.type == MatcherType.REGEX:
        desc = f'regex on "{cfg.field}": {cfg.pattern}{suffix}'
    elif cfg.type == MatcherType.HAS_PREFIX:
        prefixes = ", ".join(f'"{p}"' for p in cfg.prefixes)
        desc = f'hasPrefix([{prefixes}]) on "{cfg.field}"{suffix}'
    elif cfg.type == MatcherType.CONTAINS_ANY:
        substrings = ", ".join(f'"{s}"' for s in cfg.substrings)
        cs = " (case-sensitive)" if cfg.case_sensitive else ""
        desc = f'containsAny([{substrings}]) on "{cfg.field}"{cs}{suffix}'
    elif cfg.type == MatcherType.EXACT_MATCH:
        values = ", ".join(f'"{v}"' for v in cfg.values)
        cs = " (case-sensitive)" if cfg.case_sensitive else ""
        desc = f'exactMatch([{values}]) on "{cfg.field}"{cs}{suffix}'
    else:
        desc = str(cfg.type.value)
    if cfg.transformers:
        pre_descs = "; ".join(_describe_transformer(t) for t in cfg.transformers)
        desc = f"[pre: {pre_descs}] {desc}"
    return desc


def _describe_transformer(cfg: ConfigTransformer) -> str:
    if cfg.type == TransformerType.CONVERT_CARDINAL_NUMBERS:
        direction = cfg.direction.value if hasattr(cfg.direction, "value") else str(cfg.direction)
        output_type = cfg.output_type.value if hasattr(cfg.output_type, "value") else str(cfg.output_type)
        parts = [p for p in [direction, f"\u2192 {output_type}" if output_type else ""] if p]
        field_note = f' on "{cfg.field}"' if cfg.field and cfg.field != "name" else ""
        return f'convertCardinalNumbers({" ".join(parts)}){field_note}'
    if cfg.type == TransformerType.REGEX:
        if cfg.action == "replace":
            return f'regex "{cfg.pattern}" \u2192 "{cfg.replacement}"'
        return f'regex "{cfg.pattern}" \u2192 {cfg.action}'
    if cfg.type == TransformerType.STRIP:
        parts: list[str] = []
        if cfg.prefix:
            parts.append(f'prefix="{cfg.prefix}"')
        if cfg.suffix:
            parts.append(f'suffix="{cfg.suffix}"')
        field_note = f' on "{cfg.field}"' if cfg.field and cfg.field != "name" else ""
        return f'strip({", ".join(parts)}){field_note}'
    if cfg.type == TransformerType.SET:
        field_note = f' on "{cfg.field}"' if cfg.field and cfg.field != "name" else ""
        return f'set \u2192 "{cfg.value}"{field_note}'
    return str(cfg.type.value)


class MemberPipeline:
    """Encapsulates matcher and transformer instances for a single ConfigMember."""

    def __init__(self, member: ConfigMember, inherited_stream_profile: "str | None" = None) -> None:
        self._member = member
        self._effective_stream_profile: str | None = member.stream_profile or inherited_stream_profile
        self._matchers: list[
            WaybillMatcherRegex | WaybillMatcherHasPrefix | WaybillMatcherContainsAny | WaybillMatcherExactMatch
        ] = [
            build_matcher(cfg) for cfg in member.matchers
        ]
        self._transformers = [build_transformer(cfg) for cfg in member.transformers]
        # Fields actually needed by matchers and their pre-transformers — drives .only() to keep ORM objects lean
        self._required_fields: set[str] = (
            {cfg.field for cfg in member.matchers}
            | {t.field for cfg in member.matchers for t in cfg.transformers}
            | {"id", "name", "tvg_id", "logo_url"}
        )
        self._matcher_descs: list[str] = [_describe_matcher(cfg) for cfg in member.matchers]
        self._transformer_descs: list[str] = [_describe_transformer(cfg) for cfg in member.transformers]

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

        groups: defaultdict[str, list[StreamRecord]] = defaultdict(list)
        dropped_records: list[DroppedRecord] = []

        transformer_pairs = list(zip(
            self._transformers,
            self._transformer_descs,
            range(1, len(self._transformers) + 1),
        ))

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
                    steps.append(TransformStep(
                        transformer_index=idx,
                        transformer_desc=desc,
                        name_in=name_in,
                        name_out=None,
                    ))
                    dropped_records.append(DroppedRecord(original_name=original_name, steps=steps))
                    was_dropped = True
                    break
                steps.append(TransformStep(
                    transformer_index=idx,
                    transformer_desc=desc,
                    name_in=name_in,
                    name_out=result.name,
                ))
                working = result

            if not was_dropped:
                groups[working.name].append(
                    StreamRecord(
                        id=stream.pk,
                        original_name=original_name,
                        transformed_name=working.name,
                        tvg_id=stream.tvg_id,
                        logo_url=stream.logo_url,
                        steps=steps,
                    )
                )

        channels = sorted(
            (
                ChannelPlan(
                    name=name,
                    epg_id=_most_common(r.tvg_id for r in records),
                    logo_url=_most_common(r.logo_url for r in records),
                    stream_profile=self._effective_stream_profile,
                    streams=records,
                )
                for name, records in groups.items()
            ),
            key=lambda c: c.name,
        )
        return MemberPlan(
            member_name=self._member.name,
            matcher_descs=self._matcher_descs,
            transformer_descs=self._transformer_descs,
            channels=channels,
            dropped=dropped_records,
        )


class GroupPipeline:
    """Encapsulates processing for a single ConfigGroup (→ Dispatcharr ChannelGroup)."""

    def __init__(self, key: str, name: str, members: list[ConfigMember], inherited_stream_profile: "str | None" = None, group_stream_profile: "str | None" = None) -> None:
        self._key = key
        self._name = name
        effective = group_stream_profile or inherited_stream_profile
        self._pipelines = [MemberPipeline(m, inherited_stream_profile=effective) for m in members]

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


class WaybillPlanFormatter:
    """Renders a WaybillPlan as a human-readable tree of log lines."""

    def format(self, plan: WaybillPlan) -> list[str]:
        lines: list[str] = []
        lines.append(f"=== Waybill Plan: {plan.manifest_name} ===")

        total_channels = 0
        for profile in plan.profiles:
            lines.append(f"Profile: {profile.key}")
            for group in profile.groups:
                lines.append(f"  [{group.key}] {group.name}")
                for member in group.members:
                    lines.append(f"    {member.member_name}")
                    for i, desc in enumerate(member.matcher_descs, 1):
                        lines.append(f"      Matcher [{i}]: {desc}")
                    for i, desc in enumerate(member.transformer_descs, 1):
                        lines.append(f"      Transformer [T{i}]: {desc}")
                    for channel in member.channels:
                        stream_count = len(channel.streams)
                        total_channels += 1
                        lines.append(
                            f"      Channel: {channel.name}  ({stream_count} stream(s))"
                        )
                        if channel.epg_id:
                            lines.append(f"        EPG-ID: {channel.epg_id}")
                        if channel.logo_url:
                            lines.append(f"        Logo:   {channel.logo_url}")
                        if channel.stream_profile:
                            lines.append(f"        Stream Profile: {channel.stream_profile}")
                        for stream in channel.streams:
                            if stream.original_name != stream.transformed_name:
                                lines.append(
                                    f'        "{stream.original_name}"  →  "{stream.transformed_name}"'
                                )
                            else:
                                lines.append(f'        "{stream.original_name}"')
                            for step in stream.steps:
                                if step.name_in != step.name_out:
                                    lines.append(
                                        f'          [T{step.transformer_index}] "{step.name_in}" → "{step.name_out}"'
                                    )
                    if member.dropped:
                        lines.append(f"      Dropped: {member.dropped_count} stream(s)")
                        for rec in member.dropped:
                            drop_step = rec.steps[-1] if rec.steps else None
                            if drop_step:
                                lines.append(
                                    f'        "{rec.original_name}"  →  dropped by [T{drop_step.transformer_index}]: {drop_step.transformer_desc}'
                                )
                            else:
                                lines.append(f'        "{rec.original_name}"  →  dropped')
                            for step in rec.steps[:-1]:
                                if step.name_in != step.name_out:
                                    lines.append(
                                        f'          [T{step.transformer_index}] "{step.name_in}" → "{step.name_out}"'
                                    )

        profile_count = len(plan.profiles)
        lines.append(
            f"=== Summary: {total_channels} channel(s) across {profile_count} profile(s) ==="
        )
        return lines
