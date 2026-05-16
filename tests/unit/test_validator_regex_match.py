"""Tests for WaybillValidatorRegexMatch."""

from __future__ import annotations

import pytest

from src.validators.base import WaybillStreamValidatorBase
from src.validators.regex import WaybillValidatorRegexMatch


class TestWaybillValidatorRegexMatch:
    @pytest.mark.parametrize(
        "name, expected",
        [
            ("NBS One", True),
            ("VTN 1", False),
        ],
    )
    def test_match_result(self, name, expected, stream_factory) -> None:
        v = WaybillValidatorRegexMatch(pattern=r"^NBS", action="warn", field="name")
        assert v.validate(stream_factory(name=name)) is expected

    def test_validates_tvg_id_field(self, stream_factory) -> None:
        v = WaybillValidatorRegexMatch(
            pattern=r"\.demo$", action="warn", field="tvg_id"
        )
        assert v.validate(stream_factory(tvg_id="bbc.demo")) is True
        assert v.validate(stream_factory(tvg_id="bbc.live")) is False

    def test_action_is_preserved(self) -> None:
        v = WaybillValidatorRegexMatch(pattern=r".*", action="fail", field="name")
        assert v.action == "fail"

    def test_is_stream_validator(self) -> None:
        v = WaybillValidatorRegexMatch(pattern=r".*", action="warn", field="name")
        assert isinstance(v, WaybillStreamValidatorBase)

    def test_describe_includes_pattern_and_action(self) -> None:
        v = WaybillValidatorRegexMatch(pattern=r"^NBS", action="warn", field="name")
        desc = v.describe()
        assert "NBS" in desc
        assert "warn" in desc
