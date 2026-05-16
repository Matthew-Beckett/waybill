"""Unit tests for plan data structures and the assemble_member_plan helper.

Covers:
- WaybillPlan.has_failures()
- MemberPlan.dropped_count property
- _most_common() frequency helper
- assemble_member_plan() channel sorting, epg_id / logo_url aggregation,
  quality ordering, and dropped-record plumbing

Django's ORM Stream model is stubbed; plan types are pure Python dataclasses
with no external dependencies.
"""

from __future__ import annotations

from src.plan import WaybillPlanFormatter, _most_common, assemble_member_plan
from src.types.config import OrderStreamsBy
from src.types.plan import (
    DroppedRecord,
    GroupPlan,
    MemberPlan,
    ProfilePlan,
    StreamRecord,
    ValidatorViolation,
    WaybillPlan,
)


def _stream_record(
    id: int = 1,
    original_name: str = "NBS One",
    transformed_name: str = "NBS One",
    tvg_id: str | None = "bbc.one",
    logo_url: str | None = "https://example.com/logo.png",
) -> StreamRecord:
    return StreamRecord(
        id=id,
        original_name=original_name,
        transformed_name=transformed_name,
        tvg_id=tvg_id,
        logo_url=logo_url,
    )


def _violation(
    action: str = "warn", scope: str = "stream", target: str = "NBS One"
) -> ValidatorViolation:
    return ValidatorViolation(
        validator_index=1,
        validator_desc="test validator",
        action=action,
        scope=scope,
        target=target,
    )


def _member_plan(violations: list[ValidatorViolation] | None = None) -> MemberPlan:
    return MemberPlan(member_name="test", violations=violations or [])


class TestWaybillPlanHasFailures:
    def _plan(self, *member_plans: MemberPlan) -> WaybillPlan:
        group = GroupPlan(key="g", name="Group", members=list(member_plans))
        profile = ProfilePlan(key="p", groups=[group])
        return WaybillPlan(manifest_name="test", profiles=[profile])

    def test_returns_false_when_no_violations(self) -> None:
        plan = self._plan(_member_plan())
        assert plan.has_failures() is False

    def test_returns_false_when_only_warn_violations(self) -> None:
        plan = self._plan(_member_plan([_violation(action="warn")]))
        assert plan.has_failures() is False

    def test_returns_true_when_fail_violation_present(self) -> None:
        plan = self._plan(_member_plan([_violation(action="fail")]))
        assert plan.has_failures() is True

    def test_returns_true_when_mix_of_warn_and_fail(self) -> None:
        plan = self._plan(
            _member_plan([_violation(action="warn"), _violation(action="fail")])
        )
        assert plan.has_failures() is True

    def test_checks_across_multiple_members(self) -> None:
        plan = self._plan(
            _member_plan([_violation(action="warn")]),
            _member_plan([_violation(action="fail")]),
        )
        assert plan.has_failures() is True

    def test_empty_profiles(self) -> None:
        plan = WaybillPlan(manifest_name="test", profiles=[])
        assert plan.has_failures() is False

    def test_channel_scope_fail_also_detected(self) -> None:
        violation = _violation(action="fail", scope="channel", target="NBS One")
        plan = self._plan(_member_plan([violation]))
        assert plan.has_failures() is True


class TestMemberPlanDroppedCount:
    def test_zero_when_no_dropped(self) -> None:
        mp = MemberPlan(member_name="test", dropped=[])
        assert mp.dropped_count == 0

    def test_counts_dropped_records(self) -> None:
        dropped = [DroppedRecord(original_name=f"ch{i}") for i in range(3)]
        mp = MemberPlan(member_name="test", dropped=dropped)
        assert mp.dropped_count == 3

    def test_single_dropped_record(self) -> None:
        mp = MemberPlan(
            member_name="test", dropped=[DroppedRecord(original_name="NBS One")]
        )
        assert mp.dropped_count == 1


class TestMostCommon:
    def test_returns_most_frequent_value(self) -> None:
        assert _most_common(["a", "b", "a"]) == "a"

    def test_returns_none_when_all_none(self) -> None:
        assert _most_common([None, None]) is None

    def test_returns_none_for_empty_iterable(self) -> None:
        assert _most_common([]) is None

    def test_excludes_none_from_count(self) -> None:
        assert _most_common([None, "b", "b"]) == "b"

    def test_single_value(self) -> None:
        assert _most_common(["x"]) == "x"

    def test_tie_returns_one_of_the_tied_values(self) -> None:
        result = _most_common(["a", "b"])
        assert result in ("a", "b")

    def test_all_same_value(self) -> None:
        assert _most_common(["z", "z", "z"]) == "z"


class TestAssembleMemberPlan:
    def _raw_groups(
        self,
        channel_names: list[str],
        tvg_id: str | None = "bbc.one",
        logo_url: str | None = "https://example.com/logo.png",
    ) -> dict:
        return {
            name: [
                (
                    None,
                    _stream_record(
                        id=i,
                        original_name=name,
                        transformed_name=name,
                        tvg_id=tvg_id,
                        logo_url=logo_url,
                    ),
                )
            ]
            for i, name in enumerate(channel_names)
        }

    def test_returns_member_plan(self) -> None:
        result = assemble_member_plan(
            member_name="NBS",
            matcher_descs=["regex: NBS"],
            transformer_descs=[],
            raw_groups=self._raw_groups(["NBS One"]),
            dropped=[],
            effective_stream_profile=None,
            effective_order_streams_by=None,
        )
        assert isinstance(result, MemberPlan)

    def test_member_name_preserved(self) -> None:
        result = assemble_member_plan(
            member_name="My Member",
            matcher_descs=[],
            transformer_descs=[],
            raw_groups=self._raw_groups(["NBS One"]),
            dropped=[],
            effective_stream_profile=None,
            effective_order_streams_by=None,
        )
        assert result.member_name == "My Member"

    def test_channels_sorted_alphabetically(self) -> None:
        result = assemble_member_plan(
            member_name="test",
            matcher_descs=[],
            transformer_descs=[],
            raw_groups=self._raw_groups(["VTN 1", "NBS One", "Apex TV"]),
            dropped=[],
            effective_stream_profile=None,
            effective_order_streams_by=None,
        )
        names = [c.name for c in result.channels]
        assert names == sorted(names)

    def test_epg_id_taken_from_most_common_tvg_id(self) -> None:
        raw_groups = {
            "NBS One": [
                (
                    None,
                    _stream_record(
                        id=1,
                        original_name="NBS One",
                        transformed_name="NBS One",
                        tvg_id="bbc.one",
                    ),
                ),
                (
                    None,
                    _stream_record(
                        id=2,
                        original_name="NBS One",
                        transformed_name="NBS One",
                        tvg_id="bbc.one",
                    ),
                ),
                (
                    None,
                    _stream_record(
                        id=3,
                        original_name="NBS One",
                        transformed_name="NBS One",
                        tvg_id="other.id",
                    ),
                ),
            ]
        }
        result = assemble_member_plan(
            member_name="test",
            matcher_descs=[],
            transformer_descs=[],
            raw_groups=raw_groups,
            dropped=[],
            effective_stream_profile=None,
            effective_order_streams_by=None,
        )
        assert result.channels[0].epg_id == "bbc.one"

    def test_logo_url_taken_from_most_common(self) -> None:
        logo_a = "https://example.com/a.png"
        logo_b = "https://example.com/b.png"
        raw_groups = {
            "NBS One": [
                (
                    None,
                    _stream_record(
                        id=1,
                        original_name="NBS One",
                        transformed_name="NBS One",
                        logo_url=logo_a,
                    ),
                ),
                (
                    None,
                    _stream_record(
                        id=2,
                        original_name="NBS One",
                        transformed_name="NBS One",
                        logo_url=logo_a,
                    ),
                ),
                (
                    None,
                    _stream_record(
                        id=3,
                        original_name="NBS One",
                        transformed_name="NBS One",
                        logo_url=logo_b,
                    ),
                ),
            ]
        }
        result = assemble_member_plan(
            member_name="test",
            matcher_descs=[],
            transformer_descs=[],
            raw_groups=raw_groups,
            dropped=[],
            effective_stream_profile=None,
            effective_order_streams_by=None,
        )
        assert result.channels[0].logo_url == logo_a

    def test_stream_profile_propagated_to_channels(self) -> None:
        result = assemble_member_plan(
            member_name="test",
            matcher_descs=[],
            transformer_descs=[],
            raw_groups=self._raw_groups(["NBS One"]),
            dropped=[],
            effective_stream_profile="hd-only",
            effective_order_streams_by=None,
        )
        assert result.channels[0].stream_profile == "hd-only"

    def test_order_streams_by_propagated_to_channels(self) -> None:
        result = assemble_member_plan(
            member_name="test",
            matcher_descs=[],
            transformer_descs=[],
            raw_groups=self._raw_groups(["NBS One"]),
            dropped=[],
            effective_stream_profile=None,
            effective_order_streams_by=OrderStreamsBy.QUALITY,
        )
        assert result.channels[0].order_streams_by is OrderStreamsBy.QUALITY

    def test_dropped_records_preserved(self) -> None:
        dropped = [DroppedRecord(original_name="NBS One Dropped")]
        result = assemble_member_plan(
            member_name="test",
            matcher_descs=[],
            transformer_descs=[],
            raw_groups={},
            dropped=dropped,
            effective_stream_profile=None,
            effective_order_streams_by=None,
        )
        assert result.dropped == dropped

    def test_matcher_and_transformer_descs_preserved(self) -> None:
        result = assemble_member_plan(
            member_name="test",
            matcher_descs=["regex: ^NBS"],
            transformer_descs=["strip(prefix=UK: )"],
            raw_groups={},
            dropped=[],
            effective_stream_profile=None,
            effective_order_streams_by=None,
        )
        assert result.matcher_descs == ["regex: ^NBS"]
        assert result.transformer_descs == ["strip(prefix=UK: )"]


class TestWaybillPlanFormatter:
    def test_includes_member_scope_violations(self) -> None:
        plan = WaybillPlan(
            manifest_name="test",
            profiles=[
                ProfilePlan(
                    key="default",
                    groups=[
                        GroupPlan(
                            key="sports",
                            name="Sports",
                            members=[
                                MemberPlan(
                                    member_name="Arena Sports",
                                    validator_descs=[
                                        'count(scope="member") > 0 → fail'
                                    ],
                                    violations=[
                                        _violation(
                                            action="fail",
                                            scope="member",
                                            target="Arena Sports",
                                        )
                                    ],
                                )
                            ],
                        )
                    ],
                )
            ],
        )

        lines = WaybillPlanFormatter().format(plan)

        assert "      Violations: 1 member validation(s)" in lines
        assert '        [FAIL] [V1] "Arena Sports": test validator' in lines

    def test_quality_ordering_sorts_streams_by_resolution_descending(self) -> None:
        raw_groups = {
            "NBS One": [
                (
                    {"resolution": "1280x720", "video_bitrate": 2000.0},
                    _stream_record(
                        id=1, original_name="NBS One", transformed_name="NBS One"
                    ),
                ),
                (
                    {"resolution": "1920x1080", "video_bitrate": 4500.0},
                    _stream_record(
                        id=2, original_name="NBS One", transformed_name="NBS One"
                    ),
                ),
            ]
        }
        result = assemble_member_plan(
            member_name="test",
            matcher_descs=[],
            transformer_descs=[],
            raw_groups=raw_groups,
            dropped=[],
            effective_stream_profile=None,
            effective_order_streams_by=OrderStreamsBy.QUALITY,
        )
        streams = result.channels[0].streams
        assert streams[0].id == 2  # 1080p first
        assert streams[1].id == 1  # 720p second

    def test_quality_ordering_sets_order_reason_on_streams(self) -> None:
        raw_groups = {
            "NBS One": [
                (
                    {"resolution": "1920x1080", "video_bitrate": 4500.0},
                    _stream_record(
                        id=1, original_name="NBS One", transformed_name="NBS One"
                    ),
                ),
            ]
        }
        result = assemble_member_plan(
            member_name="test",
            matcher_descs=[],
            transformer_descs=[],
            raw_groups=raw_groups,
            dropped=[],
            effective_stream_profile=None,
            effective_order_streams_by=OrderStreamsBy.QUALITY,
        )
        assert result.channels[0].streams[0].order_reason == "quality: 1080p, 4500kbps"

    def test_no_order_streams_by_preserves_insertion_order(self) -> None:
        raw_groups = {
            "NBS One": [
                (
                    None,
                    _stream_record(
                        id=10, original_name="NBS One", transformed_name="NBS One"
                    ),
                ),
                (
                    None,
                    _stream_record(
                        id=20, original_name="NBS One", transformed_name="NBS One"
                    ),
                ),
            ]
        }
        result = assemble_member_plan(
            member_name="test",
            matcher_descs=[],
            transformer_descs=[],
            raw_groups=raw_groups,
            dropped=[],
            effective_stream_profile=None,
            effective_order_streams_by=None,
        )
        ids = [s.id for s in result.channels[0].streams]
        assert ids == [10, 20]

    def test_empty_raw_groups_produces_no_channels(self) -> None:
        result = assemble_member_plan(
            member_name="test",
            matcher_descs=[],
            transformer_descs=[],
            raw_groups={},
            dropped=[],
            effective_stream_profile=None,
            effective_order_streams_by=None,
        )
        assert result.channels == []

    def test_channel_with_none_tvg_ids_has_none_epg_id(self) -> None:
        raw_groups = {
            "NBS One": [
                (
                    None,
                    _stream_record(
                        id=1,
                        original_name="NBS One",
                        transformed_name="NBS One",
                        tvg_id=None,
                    ),
                ),
            ]
        }
        result = assemble_member_plan(
            member_name="test",
            matcher_descs=[],
            transformer_descs=[],
            raw_groups=raw_groups,
            dropped=[],
            effective_stream_profile=None,
            effective_order_streams_by=None,
        )
        assert result.channels[0].epg_id is None
