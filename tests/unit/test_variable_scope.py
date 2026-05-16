"""Tests for scoped predefined variables and template transformer integration.

Exercises that ConfigVariable instances defined at each scope level (profile,
group, member) are properly inherited by inner scopes, that inner definitions
shadow outer ones, and that named capture groups participate in scope
resolution at match time.
"""

from __future__ import annotations

import sys
import types
from types import SimpleNamespace

import pytest


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
    ) -> None:
        self.pk = pk
        self.name = name
        self.tvg_id = tvg_id
        self.logo_url = logo_url


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
    sys.modules.setdefault(_mod_name, _mod)

import src.pipeline as pipeline_module  # noqa: E402
from src.types.config import ConfigMember, ConfigVariable  # noqa: E402

pipeline_module.Stream = _StreamStub
MemberPipeline = pipeline_module.MemberPipeline


def _set_streams(*streams: _StreamStub) -> None:
    pipeline_module.Stream = _StreamStub
    _StreamStub.objects = _StreamManager(list(streams))


def _template_member(
    *,
    name: str = "Test Member",
    pattern: str,
    template_value: str,
    template_field: str = "name",
    inherited_variables: "dict[str, ConfigVariable] | None" = None,
    member_variables: "dict[str, ConfigVariable] | None" = None,
) -> MemberPipeline:
    member = ConfigMember(
        name=name,
        matchers=[{"type": "regex", "field": "name", "pattern": pattern}],
        transformers=[
            {"type": "template", "field": template_field, "value": template_value}
        ],
        variables=member_variables or {},
    )
    return MemberPipeline(
        member,
        inherited_variables=inherited_variables or {},
    )


class TestVariableScope:
    @pytest.mark.parametrize(
        "stream_name, pattern, template_value, inherited_variables, member_variables, expected_name",
        [
            # Variable defined at an outer scope (e.g. profile) is visible inside a member
            (
                "BBC One",
                r"^BBC",
                "{{ brand }} One",
                {"brand": ConfigVariable(value="British")},
                None,
                "British One",
            ),
            # Inner scope (group) variable shadows an outer scope (profile) value
            (
                "ESPN HD",
                r"^ESPN",
                "{{ network }}: ESPN",
                {"network": ConfigVariable(value="Premium Sports")},
                None,
                "Premium Sports: ESPN",
            ),
            # Member-level variable shadows an inherited value with the same name
            (
                "Sky One",
                r"^Sky",
                "{{ suffix }} Sky One",
                {"suffix": ConfigVariable(value="[Global]")},
                {"suffix": ConfigVariable(value="[Special]")},
                "[Special] Sky One",
            ),
            # Named capture group shadows a mutable predefined variable
            (
                "UK| Arsenal HD",
                r"^UK\| (?P<ch_name>.+?) (?P<quality>HD|SD)$",
                "{{ ch_name }} ({{ quality }})",
                {"ch_name": ConfigVariable(value="Default", mutable=True)},
                None,
                "Arsenal (HD)",
            ),
        ],
        ids=[
            "outer_scope_visible",
            "inner_scope_shadows",
            "member_shadows_inherited",
            "capture_shadows_mutable",
        ],
    )
    def test_scope_resolution(
        self,
        stream_name,
        pattern,
        template_value,
        inherited_variables,
        member_variables,
        expected_name,
    ) -> None:
        _set_streams(_StreamStub(pk=1, name=stream_name))
        pipeline = _template_member(
            pattern=pattern,
            template_value=template_value,
            inherited_variables=inherited_variables,
            member_variables=member_variables or {},
        )
        plan = pipeline.process()
        assert plan.channels[0].name == expected_name

    def test_captures_recorded_in_stream_record(self) -> None:
        """Named captures are stored on StreamRecord.captures for traceability."""
        _set_streams(_StreamStub(pk=1, name="UK| Arsenal HD"))
        pipeline = _template_member(
            pattern=r"^UK\| (?P<ch_name>.+?) (?P<quality>HD|SD)$",
            template_value="{{ ch_name }} ({{ quality }})",
        )
        plan = pipeline.process()
        assert len(plan.channels) == 1
        stream_record = plan.channels[0].streams[0]
        assert stream_record.captures["ch_name"] == "Arsenal"
        assert stream_record.captures["quality"] == "HD"

    def test_predefined_variables_included_in_captures(self) -> None:
        """Predefined variables are also included in StreamRecord.captures."""
        _set_streams(_StreamStub(pk=1, name="BBC One"))
        pipeline = _template_member(
            pattern=r"^BBC",
            template_value="{{ network }} One",
            inherited_variables={"network": ConfigVariable(value="British")},
        )
        plan = pipeline.process()
        stream_record = plan.channels[0].streams[0]
        assert stream_record.captures.get("network") == "British"

    def test_single_member_produces_multiple_channels(self) -> None:
        """A single member with named captures can produce many distinct channels."""
        _set_streams(
            _StreamStub(pk=1, name="UK| Arsenal HD"),
            _StreamStub(pk=2, name="UK| Chelsea SD"),
            _StreamStub(pk=3, name="UK| Liverpool HD"),
        )
        pipeline = _template_member(
            pattern=r"^UK\| (?P<ch_name>.+?) (?P<quality>HD|SD)$",
            template_value="{{ ch_name }} ({{ quality }})",
        )
        plan = pipeline.process()
        channel_names = sorted(c.name for c in plan.channels)
        assert channel_names == ["Arsenal (HD)", "Chelsea (SD)", "Liverpool (HD)"]

    def test_streams_with_same_template_output_merge_into_one_channel(self) -> None:
        """Streams whose template renders to the same value are grouped into a
        single channel."""
        _set_streams(
            _StreamStub(pk=1, name="UK| Arsenal HD"),
            _StreamStub(pk=2, name="UK| Arsenal HD"),
        )
        pipeline = _template_member(
            pattern=r"^UK\| (?P<ch_name>.+?) (?P<quality>HD|SD)$",
            template_value="{{ ch_name }} ({{ quality }})",
        )
        plan = pipeline.process()
        assert len(plan.channels) == 1
        assert len(plan.channels[0].streams) == 2
