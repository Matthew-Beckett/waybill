"""Tests for stream quality ordering in the pipeline layer.

Covers:
- _quality_key() produces correct (height, bitrate) tuples
- _quality_order_reason() produces human-readable reason strings
- MemberPipeline propagates and applies quality ordering correctly via the
  inheritance chain (profile → group → member)

Stream ORM objects are replaced with simple SimpleNamespace stubs so these
tests run without Django.
"""

from __future__ import annotations

import sys
import types
from types import SimpleNamespace

import pytest

# Stub out the Django ORM before importing pipeline

# Minimal stub for apps.channels.models.Stream
_channels_models = types.ModuleType("apps.channels.models")


class _StreamStub:
    """Lightweight stand-in for apps.channels.models.Stream."""

    objects = None  # not used in helper-function tests

    def __init__(self, **kwargs: object) -> None:
        for k, v in kwargs.items():
            setattr(self, k, v)


_channels_models.Stream = _StreamStub  # type: ignore[attr-defined]

# Stub for num2words (required by convert_cardinal_numbers transformer)
_num2words_mod = types.ModuleType("num2words")
_num2words_mod.num2words = lambda *a, **kw: ""  # type: ignore[attr-defined]

# Stub for word2number (required by convert_cardinal_numbers transformer)
_w2n_mod = types.ModuleType("word2number")
_w2n_mod.w2n = SimpleNamespace(word_to_num=lambda s: int(s))  # type: ignore[attr-defined]

# Register all stub modules so imports in pipeline.py/transformers resolve.
for _mod_name, _mod in (
    ("apps", types.ModuleType("apps")),
    ("apps.channels", types.ModuleType("apps.channels")),
    ("apps.channels.models", _channels_models),
    ("num2words", _num2words_mod),
    ("word2number", _w2n_mod),
):
    if _mod_name not in sys.modules:
        sys.modules[_mod_name] = _mod

from src.plan import _quality_key, _quality_order_reason  # noqa: E402 — after stub setup
from src.types.config import OrderStreamsBy  # noqa: E402


# _quality_key


class TestQualityKey:
    def test_returns_height_and_bitrate(self) -> None:
        stats = {"resolution": "1920x1080", "video_bitrate": 4500.0}
        assert _quality_key(stats) == (1080, 4500.0)

    def test_4k_resolution(self) -> None:
        stats = {"resolution": "3840x2160", "video_bitrate": 15000.0}
        assert _quality_key(stats) == (2160, 15000.0)

    def test_720p_resolution(self) -> None:
        stats = {"resolution": "1280x720", "video_bitrate": 2000.0}
        assert _quality_key(stats) == (720, 2000.0)

    def test_none_stats(self) -> None:
        assert _quality_key(None) == (0, 0.0)

    def test_empty_dict(self) -> None:
        assert _quality_key({}) == (0, 0.0)

    def test_missing_resolution_key(self) -> None:
        # Bitrate is still used as a tiebreaker even when resolution is absent.
        assert _quality_key({"video_bitrate": 4500.0}) == (0, 4500.0)

    def test_malformed_resolution(self) -> None:
        assert _quality_key({"resolution": "notaresolution"}) == (0, 0.0)

    def test_missing_bitrate_defaults_to_zero(self) -> None:
        stats = {"resolution": "1920x1080"}
        assert _quality_key(stats) == (1080, 0.0)

    def test_none_bitrate_defaults_to_zero(self) -> None:
        stats = {"resolution": "1920x1080", "video_bitrate": None}
        assert _quality_key(stats) == (1080, 0.0)

    def test_sort_order_descending(self) -> None:
        """Higher resolution + higher bitrate should sort first when reversed."""
        keys = [
            _quality_key({"resolution": "1280x720", "video_bitrate": 2000.0}),
            _quality_key({"resolution": "1920x1080", "video_bitrate": 4500.0}),
            _quality_key(None),
            _quality_key({"resolution": "3840x2160", "video_bitrate": 15000.0}),
        ]
        assert sorted(keys, reverse=True) == [
            (2160, 15000.0),
            (1080, 4500.0),
            (720, 2000.0),
            (0, 0.0),
        ]


# _quality_order_reason


class TestQualityOrderReason:
    def test_returns_height_and_bitrate_string(self) -> None:
        stats = {"resolution": "1920x1080", "video_bitrate": 4500.0}
        assert _quality_order_reason(stats) == "quality: 1080p, 4500kbps"

    def test_formats_bitrate_as_int(self) -> None:
        stats = {"resolution": "1280x720", "video_bitrate": 2000.123}
        reason = _quality_order_reason(stats)
        assert reason == "quality: 720p, 2000kbps"

    def test_none_stats_returns_no_stats(self) -> None:
        assert _quality_order_reason(None) == "quality: no stats"

    def test_empty_dict_returns_no_stats(self) -> None:
        assert _quality_order_reason({}) == "quality: no stats"

    def test_missing_resolution_returns_no_stats(self) -> None:
        assert _quality_order_reason({"video_bitrate": 4500.0}) == "quality: no stats"

    def test_malformed_resolution_returns_no_stats(self) -> None:
        assert _quality_order_reason({"resolution": "bad"}) == "quality: no stats"


# OrderStreamsBy inheritance via pipeline constructors
# We test the inheritance chain by inspecting MemberPipeline._effective_order_streams_by
# directly, without running the full ORM query.


def _make_member_pipeline(
    *,
    member_osb: "OrderStreamsBy | None" = None,
    inherited_osb: "OrderStreamsBy | None" = None,
) -> object:
    """Build a MemberPipeline with no matchers or transformers."""
    from src.pipeline import MemberPipeline
    from src.types.config import ConfigMember

    member = ConfigMember(name="test", order_streams_by=member_osb)
    return MemberPipeline(member, inherited_order_streams_by=inherited_osb)


class TestMemberPipelineInheritance:
    def test_member_osb_takes_precedence(self) -> None:
        mp = _make_member_pipeline(
            member_osb=OrderStreamsBy.QUALITY,
            inherited_osb=None,
        )
        assert mp._effective_order_streams_by is OrderStreamsBy.QUALITY

    def test_inherits_when_member_is_none(self) -> None:
        mp = _make_member_pipeline(
            member_osb=None,
            inherited_osb=OrderStreamsBy.QUALITY,
        )
        assert mp._effective_order_streams_by is OrderStreamsBy.QUALITY

    def test_both_none_gives_none(self) -> None:
        mp = _make_member_pipeline(member_osb=None, inherited_osb=None)
        assert mp._effective_order_streams_by is None

    def test_stream_stats_added_to_required_fields_for_quality(self) -> None:
        mp = _make_member_pipeline(member_osb=OrderStreamsBy.QUALITY)
        assert "stream_stats" in mp._required_fields

    def test_stream_stats_not_added_when_no_ordering(self) -> None:
        mp = _make_member_pipeline(member_osb=None, inherited_osb=None)
        assert "stream_stats" not in mp._required_fields


def _make_group_pipeline_effective(
    *,
    group_osb: "OrderStreamsBy | None",
    inherited_osb: "OrderStreamsBy | None",
) -> "OrderStreamsBy | None":
    """Return the effective order_streams_by that GroupPipeline passes to MemberPipeline."""
    from src.pipeline import GroupPipeline
    from src.types.config import ConfigMember

    member = ConfigMember(name="m")
    gp = GroupPipeline(
        key="g",
        name="G",
        members=[member],
        inherited_order_streams_by=inherited_osb,
        group_order_streams_by=group_osb,
    )
    assert len(gp._pipelines) == 1
    return gp._pipelines[0]._effective_order_streams_by


class TestGroupPipelineOrderStreamsBy:
    def test_group_osb_overrides_inherited(self) -> None:
        effective = _make_group_pipeline_effective(
            group_osb=OrderStreamsBy.QUALITY,
            inherited_osb=None,
        )
        assert effective is OrderStreamsBy.QUALITY

    def test_inherited_used_when_group_is_none(self) -> None:
        effective = _make_group_pipeline_effective(
            group_osb=None,
            inherited_osb=OrderStreamsBy.QUALITY,
        )
        assert effective is OrderStreamsBy.QUALITY

    def test_none_when_both_absent(self) -> None:
        effective = _make_group_pipeline_effective(
            group_osb=None,
            inherited_osb=None,
        )
        assert effective is None
