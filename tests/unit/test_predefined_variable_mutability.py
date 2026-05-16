"""Tests for predefined variable mutability enforcement in the pipeline.

An immutable ConfigVariable (mutable=False) must raise ValueError when a
named capture group attempts to override it.  A mutable one (mutable=True,
the default) must be silently overridden.
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

_CAPTURE_PATTERN = r"^UK\| (?P<ch_name>.+?) (?P<quality>HD|SD)$"


def _set_streams(*streams: _StreamStub) -> None:
    pipeline_module.Stream = _StreamStub
    _StreamStub.objects = _StreamManager(list(streams))


class TestMutableVariable:
    @pytest.mark.parametrize(
        "variable_spec, stream_name, template_value, expected",
        [
            # Explicit mutable=True dict — capture replaces it.
            # quality must also be declared so the regex capture reaches the template.
            (
                {
                    "ch_name": {"value": "Default", "mutable": True},
                    "quality": {"value": "", "mutable": True},
                },
                "UK| Arsenal HD",
                "{{ ch_name }} ({{ quality }})",
                "Arsenal (HD)",
            ),
            # Shorthand scalar notation (mutable=True by default) — capture replaces it
            (
                {"ch_name": "Fallback"},
                "UK| Chelsea SD",
                "{{ ch_name }}",
                "Chelsea",
            ),
        ],
        ids=["explicit_mutable_true", "shorthand_scalar"],
    )
    def test_mutable_variable_overridden_by_capture(
        self, variable_spec, stream_name, template_value, expected
    ) -> None:
        _set_streams(_StreamStub(pk=1, name=stream_name))
        member = ConfigMember(
            name="Sports Factory",
            matchers=[{"type": "regex", "field": "name", "pattern": _CAPTURE_PATTERN}],
            transformers=[
                {"type": "template", "field": "name", "value": template_value}
            ],
            variables=variable_spec,
        )
        plan = MemberPipeline(member).process()
        assert plan.channels[0].name == expected


class TestImmutableVariable:
    @pytest.mark.parametrize(
        "member_variables, inherited_variables",
        [
            # Immutable variable declared directly on the member
            ({"brand": {"value": "Arena", "mutable": False}}, None),
            # Immutable variable inherited from a parent scope
            ({}, {"brand": ConfigVariable(value="Arena", mutable=False)}),
        ],
        ids=["member_scope", "inherited_scope"],
    )
    def test_immutable_variable_raises_on_capture_collision(
        self, member_variables, inherited_variables
    ) -> None:
        _set_streams(_StreamStub(pk=1, name="UK| Arsenal HD"))
        member = ConfigMember(
            name="Sports Factory",
            matchers=[
                {
                    "type": "regex",
                    "field": "name",
                    "pattern": r"^UK\| (?P<brand>.+?) (?P<quality>HD|SD)$",
                }
            ],
            transformers=[
                {"type": "template", "field": "name", "value": "{{ brand }}"}
            ],
            variables=member_variables,
        )
        pipeline = MemberPipeline(member, inherited_variables=inherited_variables or {})
        with pytest.raises(ValueError, match="immutable"):
            pipeline.process()

    def test_immutable_variable_not_captured_does_not_raise(self) -> None:
        """An immutable variable is fine as long as no capture group shares its name."""
        _set_streams(_StreamStub(pk=1, name="UK| Arsenal HD"))
        member = ConfigMember(
            name="Sports Factory",
            matchers=[
                {
                    "type": "regex",
                    "field": "name",
                    "pattern": r"^UK\| (?P<ch_name>.+?) (?P<quality>HD|SD)$",
                }
            ],
            transformers=[
                {
                    "type": "template",
                    "field": "name",
                    # ch_name must be declared so the capture reaches the template.
                    "value": "{{ brand }}: {{ ch_name }}",
                }
            ],
            variables={
                "brand": {"value": "Arena", "mutable": False},
                "ch_name": {"value": "", "mutable": True},
            },
        )
        plan = MemberPipeline(member).process()
        assert plan.channels[0].name == "Arena: Arsenal"

    def test_error_message_includes_member_name(self) -> None:
        """The error message must identify the member by name for diagnosability."""
        _set_streams(_StreamStub(pk=1, name="UK| Arsenal HD"))
        member = ConfigMember(
            name="My Named Member",
            matchers=[
                {"type": "regex", "field": "name", "pattern": r"^UK\| (?P<brand>.+)$"}
            ],
            transformers=[],
            variables={"brand": {"value": "Arena", "mutable": False}},
        )
        with pytest.raises(ValueError, match="My Named Member"):
            MemberPipeline(member).process()
