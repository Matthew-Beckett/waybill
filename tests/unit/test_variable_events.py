"""Tests for VariableEvent emission and StreamRecord.variable_events.

Verifies that the pipeline emits correctly typed variable events throughout
stream processing:

- ``init``             — predefined variable initial values
- ``capture_override`` — regex capture group overwrites a declared predefined variable
- ``capture_discarded``— regex capture group name not declared in any variables block
- ``template_read``    — transformer template expression consumed a variable
"""

from __future__ import annotations

import sys
import types
from types import SimpleNamespace


# ---------------------------------------------------------------------------
# Module stubs (replicated from other unit-test files so this module is
# self-contained and does not depend on test execution order).
# ---------------------------------------------------------------------------


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
from src.types.plan import VariableEvent  # noqa: E402

pipeline_module.Stream = _StreamStub
MemberPipeline = pipeline_module.MemberPipeline


def _set_streams(*streams: _StreamStub) -> None:
    pipeline_module.Stream = _StreamStub
    _StreamStub.objects = _StreamManager(list(streams))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _events_of_type(
    events: list[VariableEvent], event_type: str
) -> list[VariableEvent]:
    return [e for e in events if e.event_type == event_type]


def _find_event(
    events: list[VariableEvent], event_type: str, name: str
) -> VariableEvent | None:
    for ev in events:
        if ev.event_type == event_type and ev.name == name:
            return ev
    return None


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestInitEvents:
    def test_predefined_variables_emit_init_events(self) -> None:
        """Each predefined variable (from any scope) must produce an init event."""
        _set_streams(_StreamStub(pk=1, name="NBS One"))
        member = ConfigMember(
            name="Test",
            matchers=[{"type": "regex", "field": "name", "pattern": r"^NBS"}],
            transformers=[{"type": "set", "field": "name", "value": "NBS One"}],
            variables={"network": ConfigVariable(value="British", mutable=True)},
        )
        plan = MemberPipeline(member).process()
        events = plan.channels[0].streams[0].variable_events
        init_events = _events_of_type(events, "init")
        names = {e.name for e in init_events}
        assert "network" in names

    def test_init_event_value_is_predefined_value(self) -> None:
        _set_streams(_StreamStub(pk=1, name="NBS One"))
        member = ConfigMember(
            name="Test",
            matchers=[{"type": "regex", "field": "name", "pattern": r"^NBS"}],
            transformers=[{"type": "set", "field": "name", "value": "static"}],
            variables={"brand": ConfigVariable(value="ArenaTV", mutable=True)},
        )
        plan = MemberPipeline(member).process()
        events = plan.channels[0].streams[0].variable_events
        ev = _find_event(events, "init", "brand")
        assert ev is not None
        assert ev.value == "ArenaTV"
        assert ev.source == "predefined"


class TestCaptureOverrideEvents:
    def test_declared_capture_emits_override_event(self) -> None:
        """A capture group that matches a declared variable emits capture_override."""
        _set_streams(_StreamStub(pk=1, name="UK| Northgate HD"))
        member = ConfigMember(
            name="Sports",
            matchers=[
                {
                    "type": "regex",
                    "field": "name",
                    "pattern": r"^UK\| (?P<ch_name>.+?) (?P<quality>HD|SD)$",
                }
            ],
            transformers=[
                {"type": "template", "field": "name", "value": "{{ ch_name }}"}
            ],
            variables={
                "ch_name": ConfigVariable(value="Default", mutable=True),
                "quality": ConfigVariable(value="", mutable=True),
            },
        )
        plan = MemberPipeline(member).process()
        events = plan.channels[0].streams[0].variable_events
        ev = _find_event(events, "capture_override", "ch_name")
        assert ev is not None
        assert ev.value == "Northgate"
        assert ev.old_value == "Default"

    def test_override_event_source_identifies_matcher(self) -> None:
        _set_streams(_StreamStub(pk=1, name="UK| Northgate HD"))
        member = ConfigMember(
            name="Sports",
            matchers=[
                {
                    "type": "regex",
                    "field": "name",
                    "pattern": r"^UK\| (?P<ch_name>.+?) (?P<quality>HD|SD)$",
                }
            ],
            transformers=[
                {"type": "template", "field": "name", "value": "{{ ch_name }}"}
            ],
            variables={
                "ch_name": ConfigVariable(value="", mutable=True),
                "quality": ConfigVariable(value="", mutable=True),
            },
        )
        plan = MemberPipeline(member).process()
        events = plan.channels[0].streams[0].variable_events
        ev = _find_event(events, "capture_override", "ch_name")
        assert ev is not None
        assert "matcher #1" in ev.source


class TestCaptureDiscardedEvents:
    def test_undeclared_capture_emits_discarded_event(self) -> None:
        """A capture group not in any variables block emits capture_discarded."""
        _set_streams(_StreamStub(pk=1, name="UK| Northgate HD"))
        member = ConfigMember(
            name="Sports",
            matchers=[
                {
                    "type": "regex",
                    "field": "name",
                    # ch_name is declared; quality is NOT declared
                    "pattern": r"^UK\| (?P<ch_name>.+?) (?P<quality>HD|SD)$",
                }
            ],
            transformers=[
                {"type": "template", "field": "name", "value": "{{ ch_name }}"}
            ],
            variables={"ch_name": ConfigVariable(value="", mutable=True)},
        )
        plan = MemberPipeline(member).process()
        events = plan.channels[0].streams[0].variable_events
        ev = _find_event(events, "capture_discarded", "quality")
        assert ev is not None
        assert ev.value == "HD"

    def test_discarded_capture_not_in_stream_record_captures(self) -> None:
        """A discarded capture must NOT appear in StreamRecord.captures."""
        _set_streams(_StreamStub(pk=1, name="UK| Northgate HD"))
        member = ConfigMember(
            name="Sports",
            matchers=[
                {
                    "type": "regex",
                    "field": "name",
                    "pattern": r"^UK\| (?P<ch_name>.+?) (?P<quality>HD|SD)$",
                }
            ],
            transformers=[
                {"type": "template", "field": "name", "value": "{{ ch_name }}"}
            ],
            variables={"ch_name": ConfigVariable(value="", mutable=True)},
        )
        plan = MemberPipeline(member).process()
        captures = plan.channels[0].streams[0].captures
        assert "quality" not in captures
        assert captures["ch_name"] == "Northgate"


class TestTemplateReadEvents:
    def test_template_read_event_emitted_for_each_referenced_variable(self) -> None:
        """A template_read event must appear for each variable referenced in a transformer."""
        _set_streams(_StreamStub(pk=1, name="UK| Northgate HD"))
        member = ConfigMember(
            name="Sports",
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
                    "value": "{{ ch_name }} ({{ quality }})",
                }
            ],
            variables={
                "ch_name": ConfigVariable(value="", mutable=True),
                "quality": ConfigVariable(value="", mutable=True),
            },
        )
        plan = MemberPipeline(member).process()
        events = plan.channels[0].streams[0].variable_events
        read_events = _events_of_type(events, "template_read")
        read_names = {e.name for e in read_events}
        assert "ch_name" in read_names
        assert "quality" in read_names

    def test_template_read_event_carries_resolved_value(self) -> None:
        _set_streams(_StreamStub(pk=1, name="UK| Northgate HD"))
        member = ConfigMember(
            name="Sports",
            matchers=[
                {
                    "type": "regex",
                    "field": "name",
                    "pattern": r"^UK\| (?P<ch_name>.+?) (?P<quality>HD|SD)$",
                }
            ],
            transformers=[
                {"type": "template", "field": "name", "value": "{{ ch_name }}"}
            ],
            variables={
                "ch_name": ConfigVariable(value="", mutable=True),
                "quality": ConfigVariable(value="", mutable=True),
            },
        )
        plan = MemberPipeline(member).process()
        events = plan.channels[0].streams[0].variable_events
        ev = _find_event(events, "template_read", "ch_name")
        assert ev is not None
        assert ev.value == "Northgate"

    def test_template_read_event_source_identifies_transformer(self) -> None:
        _set_streams(_StreamStub(pk=1, name="UK| Northgate HD"))
        member = ConfigMember(
            name="Sports",
            matchers=[
                {
                    "type": "regex",
                    "field": "name",
                    "pattern": r"^UK\| (?P<ch_name>.+?) (?P<quality>HD|SD)$",
                }
            ],
            transformers=[
                {"type": "template", "field": "name", "value": "{{ ch_name }}"}
            ],
            variables={
                "ch_name": ConfigVariable(value="", mutable=True),
                "quality": ConfigVariable(value="", mutable=True),
            },
        )
        plan = MemberPipeline(member).process()
        events = plan.channels[0].streams[0].variable_events
        ev = _find_event(events, "template_read", "ch_name")
        assert ev is not None
        assert "transformer #1" in ev.source

    def test_no_template_read_events_for_non_template_transformer(self) -> None:
        """A set transformer with a literal (no template syntax) produces no read events."""
        _set_streams(_StreamStub(pk=1, name="UK| Northgate HD"))
        member = ConfigMember(
            name="Sports",
            matchers=[{"type": "regex", "field": "name", "pattern": r"^UK\|"}],
            transformers=[{"type": "set", "field": "name", "value": "Static Name"}],
            variables={},
        )
        plan = MemberPipeline(member).process()
        events = plan.channels[0].streams[0].variable_events
        read_events = _events_of_type(events, "template_read")
        assert read_events == []


class TestEventOrdering:
    def test_events_appear_in_pipeline_order(self) -> None:
        """Events must be ordered: init → capture events → template_read events."""
        _set_streams(_StreamStub(pk=1, name="UK| Northgate HD"))
        member = ConfigMember(
            name="Sports",
            matchers=[
                {
                    "type": "regex",
                    "field": "name",
                    "pattern": r"^UK\| (?P<ch_name>.+?) (?P<quality>HD|SD)$",
                }
            ],
            transformers=[
                {"type": "template", "field": "name", "value": "{{ ch_name }}"}
            ],
            variables={
                "ch_name": ConfigVariable(value="Default", mutable=True),
                "quality": ConfigVariable(value="", mutable=True),
            },
        )
        plan = MemberPipeline(member).process()
        events = plan.channels[0].streams[0].variable_events
        types_in_order = [e.event_type for e in events]

        # All inits must come before any captures or reads
        last_init = max(
            (i for i, t in enumerate(types_in_order) if t == "init"), default=-1
        )
        first_capture = min(
            (
                i
                for i, t in enumerate(types_in_order)
                if t in ("capture_override", "capture_discarded")
            ),
            default=len(types_in_order),
        )
        first_read = min(
            (i for i, t in enumerate(types_in_order) if t == "template_read"),
            default=len(types_in_order),
        )
        assert last_init < first_capture
        assert first_capture < first_read
