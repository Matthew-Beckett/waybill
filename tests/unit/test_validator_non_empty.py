"""Tests for WaybillValidatorNonEmpty."""

from __future__ import annotations

import pytest

from src.validators.base import WaybillStreamValidatorBase
from src.validators.non_empty import WaybillValidatorNonEmpty


class TestWaybillValidatorNonEmpty:
    @pytest.mark.parametrize(
        "field, stream_kwargs, expected",
        [
            ("name", {"name": "BBC One"}, True),
            ("name", {"name": ""}, False),
            ("tvg_id", {"tvg_id": "bbc.one"}, True),
            ("tvg_id", {"tvg_id": ""}, False),
        ],
    )
    def test_validates_field(
        self, field, stream_kwargs, expected, stream_factory
    ) -> None:
        v = WaybillValidatorNonEmpty(action="warn", field=field)
        assert v.validate(stream_factory(**stream_kwargs)) is expected

    def test_action_is_preserved(self) -> None:
        v = WaybillValidatorNonEmpty(action="fail", field="name")
        assert v.action == "fail"

    def test_is_stream_validator(self) -> None:
        v = WaybillValidatorNonEmpty(action="warn", field="name")
        assert isinstance(v, WaybillStreamValidatorBase)

    def test_describe_includes_field_and_action(self) -> None:
        v = WaybillValidatorNonEmpty(action="warn", field="tvg_id")
        desc = v.describe()
        assert "tvg_id" in desc
        assert "warn" in desc
