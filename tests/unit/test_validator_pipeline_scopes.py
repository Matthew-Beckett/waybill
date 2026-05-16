"""Focused tests for validator scope execution in MemberPipeline."""

from __future__ import annotations

import sys
import types
from types import SimpleNamespace


class _QuerySetStub:
    def __init__(self, streams: list[object]) -> None:
        self._streams = streams

    def only(self, *fields: str) -> "_QuerySetStub":
        return self

    def iterator(self, chunk_size: int = 1000):
        del chunk_size
        return iter(self._streams)


class _ManagerStub:
    def __init__(self, streams: list[object]) -> None:
        self._streams = streams

    def filter(self, q_filter: object) -> _QuerySetStub:
        del q_filter
        return _QuerySetStub(self._streams)


class _StreamStub:
    objects = _ManagerStub([])

    def __init__(self, **kwargs: object) -> None:
        for key, value in kwargs.items():
            setattr(self, key, value)


_channels_models = types.ModuleType("apps.channels.models")
_channels_models.Stream = _StreamStub  # type: ignore[attr-defined]

_num2words_mod = types.ModuleType("num2words")
_num2words_mod.num2words = lambda *a, **kw: ""  # type: ignore[attr-defined]

_w2n_mod = types.ModuleType("word2number")
_w2n_mod.w2n = SimpleNamespace(word_to_num=lambda s: int(s))  # type: ignore[attr-defined]

for _mod_name, _mod in (
    ("apps", types.ModuleType("apps")),
    ("apps.channels", types.ModuleType("apps.channels")),
    ("apps.channels.models", _channels_models),
    ("num2words", _num2words_mod),
    ("word2number", _w2n_mod),
):
    if _mod_name not in sys.modules:
        sys.modules[_mod_name] = _mod

import src.pipeline as pipeline_module  # noqa: E402
from src.types.config import (  # noqa: E402
    ConfigMember,
    ConfigValidator,
    ValidatorAction,
    ValidatorOperator,
    ValidatorScope,
    ValidatorType,
)

pipeline_module.Stream = _StreamStub
MemberPipeline = pipeline_module.MemberPipeline


def _stream(pk: int, name: str) -> _StreamStub:
    return _StreamStub(pk=pk, name=name, tvg_id="", logo_url="")


def _set_streams(streams: list[_StreamStub]) -> None:
    pipeline_module.Stream = _StreamStub
    _StreamStub.objects = _ManagerStub(streams)


class TestMemberPipelineValidatorScopes:
    def test_member_scope_count_counts_channels_not_streams(self) -> None:
        _set_streams(
            [
                _stream(1, "NBS One"),
                _stream(2, "NBS One"),
            ]
        )
        member = ConfigMember(
            name="NBS One",
            validators=[
                ConfigValidator(
                    type=ValidatorType.COUNT,
                    operator=ValidatorOperator.EQ,
                    value=1,
                    scope=ValidatorScope.MEMBER,
                )
            ],
        )

        result = MemberPipeline(member).process()

        assert len(result.channels) == 1
        assert len(result.channels[0].streams) == 2
        assert result.violations == []

    def test_member_scope_count_fires_when_no_channels_are_produced(self) -> None:
        _set_streams([])
        member = ConfigMember(
            name="Missing Feed",
            validators=[
                ConfigValidator(
                    type=ValidatorType.COUNT,
                    operator=ValidatorOperator.GT,
                    value=0,
                    action=ValidatorAction.FAIL,
                )
            ],
        )

        result = MemberPipeline(member).process()

        assert result.channels == []
        assert len(result.violations) == 1
        assert result.violations[0].scope == "member"
        assert result.violations[0].target == "Missing Feed"

    def test_channel_scope_count_still_counts_streams_per_channel(self) -> None:
        _set_streams(
            [
                _stream(1, "NBS One"),
                _stream(2, "NBS One"),
            ]
        )
        member = ConfigMember(
            name="NBS One",
            validators=[
                ConfigValidator(
                    type=ValidatorType.COUNT,
                    operator=ValidatorOperator.EQ,
                    value=2,
                    scope=ValidatorScope.CHANNEL,
                )
            ],
        )

        result = MemberPipeline(member).process()

        assert result.violations == []
