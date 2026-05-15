"""Tests for WaybillValidatorCountChannel."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from src.types.plan import ChannelPlan
from src.validators.base import WaybillChannelValidatorBase
from src.validators.count import WaybillValidatorCountChannel


def _channel(count: int) -> ChannelPlan:
    return ChannelPlan(
        name="ch",
        streams=[
            SimpleNamespace(id=i, transformed_name=f"ch{i}") for i in range(count)
        ],
    )


@pytest.mark.parametrize(
    "operator, threshold, record_count, expected",
    [
        ("gt", 0, 1, True),
        ("gt", 1, 1, False),
        ("gte", 1, 1, True),
        ("gte", 2, 1, False),
        ("lt", 5, 3, True),
        ("lt", 3, 3, False),
        ("lte", 3, 3, True),
        ("lte", 2, 3, False),
        ("eq", 2, 2, True),
        ("eq", 2, 3, False),
        ("neq", 0, 2, True),
        ("neq", 2, 2, False),
    ],
)
def test_count_operator(operator, threshold, record_count, expected) -> None:
    v = WaybillValidatorCountChannel(operator, threshold)
    assert v.validate(_channel(record_count)) is expected


class TestWaybillValidatorCountChannel:
    def test_zero_streams_gt_zero_fails(self) -> None:
        assert WaybillValidatorCountChannel("gt", 0).validate(_channel(0)) is False

    def test_zero_streams_eq_zero_passes(self) -> None:
        assert WaybillValidatorCountChannel("eq", 0).validate(_channel(0)) is True

    def test_action_is_preserved(self) -> None:
        v = WaybillValidatorCountChannel("gt", 0, action="fail")
        assert v.action == "fail"

    def test_is_channel_validator(self) -> None:
        v = WaybillValidatorCountChannel("gt", 0)
        assert isinstance(v, WaybillChannelValidatorBase)

    def test_describe_includes_operator_value_and_action(self) -> None:
        v = WaybillValidatorCountChannel("gt", 0, action="warn")
        desc = v.describe()
        assert ">" in desc
        assert "0" in desc
        assert "warn" in desc
