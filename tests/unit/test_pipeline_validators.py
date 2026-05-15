"""Pipeline-level regression tests for validator scoping.

These tests stub the minimal Django/Dispatcharr surfaces needed to exercise
MemberPipeline.process() without importing the full runtime.
"""

from __future__ import annotations

import sys
import types
from types import SimpleNamespace


class _Q:
    def __init__(self, **kwargs: object) -> None:
        self.kwargs = kwargs

    def __and__(self, other: "_Q") -> "_Q":
        return self

    def __or__(self, other: "_Q") -> "_Q":
        return self


class _StreamQuerySet:
    def __init__(self, streams: list[object]) -> None:
        self._streams = streams

    def only(self, *fields: object) -> "_StreamQuerySet":
        del fields
        return self

    def iterator(self, chunk_size: int = 1000):
        del chunk_size
        return iter(self._streams)


class _StreamManager:
    def __init__(self, streams: list[object]) -> None:
        self._streams = streams

    def filter(self, q_filter: object) -> _StreamQuerySet:
        del q_filter
        return _StreamQuerySet(self._streams)


class _StreamStub:
    objects = _StreamManager([])

    def __init__(
        self,
        *,
        pk: int,
        name: str,
        tvg_id: str | None = None,
        logo_url: str | None = None,
        stream_stats: dict | None = None,
    ) -> None:
        self.pk = pk
        self.name = name
        self.tvg_id = tvg_id
        self.logo_url = logo_url
        self.stream_stats = stream_stats


_channels_models = types.ModuleType("apps.channels.models")
_channels_models.Stream = _StreamStub  # type: ignore[attr-defined]

_django_models = types.ModuleType("django.db.models")
_django_models.Q = _Q  # type: ignore[attr-defined]

_num2words_mod = types.ModuleType("num2words")
_num2words_mod.num2words = lambda *args, **kwargs: ""  # type: ignore[attr-defined]

_w2n_mod = types.ModuleType("word2number")
_w2n_mod.w2n = SimpleNamespace(word_to_num=lambda s: int(s))  # type: ignore[attr-defined]

for _mod_name, _mod in (
    ("apps", types.ModuleType("apps")),
    ("apps.channels", types.ModuleType("apps.channels")),
    ("apps.channels.models", _channels_models),
    ("django", types.ModuleType("django")),
    ("django.db", types.ModuleType("django.db")),
    ("django.db.models", _django_models),
    ("num2words", _num2words_mod),
    ("word2number", _w2n_mod),
):
    sys.modules[_mod_name] = _mod

import src.pipeline as pipeline_module  # noqa: E402
from src.types.config import ConfigMember  # noqa: E402

pipeline_module.Stream = _StreamStub
MemberPipeline = pipeline_module.MemberPipeline


def _set_streams(*streams: _StreamStub) -> None:
    pipeline_module.Stream = _StreamStub
    _StreamStub.objects = _StreamManager(list(streams))


def test_member_scope_count_violates_when_no_channels_are_built() -> None:
    _set_streams()
    member = ConfigMember(
        name="Arena Sports",
        validators=[
            {
                "type": "count",
                "operator": "gt",
                "value": 0,
                "scope": "member",
                "action": "warn",
            }
        ],
    )

    result = MemberPipeline(member).process()

    assert result.channels == []
    assert len(result.violations) == 1
    assert result.violations[0].scope == "member"
    assert result.violations[0].target == "Arena Sports"


def test_channel_scope_non_empty_uses_assembled_epg_id() -> None:
    _set_streams(
        _StreamStub(pk=1, name="BBC One", tvg_id="bbc.one"),
        _StreamStub(pk=2, name="BBC One", tvg_id="bbc.one"),
        _StreamStub(pk=3, name="BBC One", tvg_id=""),
    )
    member = ConfigMember(
        name="BBC One",
        validators=[
            {
                "type": "nonEmpty",
                "field": "tvg_id",
                "scope": "channel",
                "action": "warn",
            }
        ],
    )

    result = MemberPipeline(member).process()

    assert [channel.name for channel in result.channels] == ["BBC One"]
    assert result.channels[0].epg_id == "bbc.one"
    assert result.violations == []
