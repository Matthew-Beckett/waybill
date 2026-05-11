"""Tests for the orderStreamsBy configuration property.

Covers:
- OrderStreamsBy enum coercion at all three scope levels
- Invalid values raise ValueError
- null / None clears the value
- Inheritance chain: profile → group → member
"""

from __future__ import annotations

import pytest

from src.types.config import (
    ConfigGroup,
    ConfigMember,
    ConfigProfile,
    ConfigSpec,
    OrderStreamsBy,
    WaybillConfig,
)


# Helpers


def _make_config(spec_payload: dict) -> WaybillConfig:
    return WaybillConfig(
        kind="WaybillConfig",
        version="v1alpha1",
        metadata={"name": "test"},
        spec=spec_payload,
    )


def _profile_dict(
    *,
    profile_osb: object = None,
    group_osb: object = None,
    member_osb: object = None,
) -> dict:
    return {
        "profiles": {
            "p": {
                "name": "P",
                "orderStreamsBy": profile_osb,
                "groups": {
                    "g": {
                        "name": "G",
                        "orderStreamsBy": group_osb,
                        "members": [
                            {
                                "name": "m",
                                "orderStreamsBy": member_osb,
                            }
                        ],
                    }
                },
            }
        }
    }


# Profile-level coercion


def test_profile_order_streams_by_quality() -> None:
    cfg = _make_config(_profile_dict(profile_osb="quality"))
    profile = cfg.spec.profiles["p"]
    assert profile.order_streams_by is OrderStreamsBy.QUALITY


def test_profile_order_streams_by_none_when_absent() -> None:
    cfg = _make_config(_profile_dict())
    assert cfg.spec.profiles["p"].order_streams_by is None


def test_profile_order_streams_by_null_yaml() -> None:
    cfg = _make_config(_profile_dict(profile_osb=None))
    assert cfg.spec.profiles["p"].order_streams_by is None


def test_profile_order_streams_by_invalid_raises() -> None:
    with pytest.raises(ValueError):
        _make_config(_profile_dict(profile_osb="random"))


# Group-level coercion


def test_group_order_streams_by_quality() -> None:
    cfg = _make_config(_profile_dict(group_osb="quality"))
    group = cfg.spec.profiles["p"].groups["g"]
    assert group.order_streams_by is OrderStreamsBy.QUALITY


def test_group_order_streams_by_none_when_absent() -> None:
    cfg = _make_config(_profile_dict())
    assert cfg.spec.profiles["p"].groups["g"].order_streams_by is None


def test_group_order_streams_by_null_yaml() -> None:
    cfg = _make_config(_profile_dict(group_osb=None))
    assert cfg.spec.profiles["p"].groups["g"].order_streams_by is None


# Member-level coercion


def test_member_order_streams_by_quality() -> None:
    cfg = _make_config(_profile_dict(member_osb="quality"))
    member = cfg.spec.profiles["p"].groups["g"].members[0]
    assert member.order_streams_by is OrderStreamsBy.QUALITY


def test_member_order_streams_by_none_when_absent() -> None:
    cfg = _make_config(_profile_dict())
    assert cfg.spec.profiles["p"].groups["g"].members[0].order_streams_by is None


def test_member_order_streams_by_null_yaml() -> None:
    cfg = _make_config(_profile_dict(member_osb=None))
    assert cfg.spec.profiles["p"].groups["g"].members[0].order_streams_by is None


# Inheritance chain


def test_inheritance_profile_to_group_to_member() -> None:
    """Profile sets quality; group and member inherit (both absent)."""
    cfg = _make_config(_profile_dict(profile_osb="quality"))
    assert cfg.spec.profiles["p"].order_streams_by is OrderStreamsBy.QUALITY
    # The config dataclasses store their own declared values only;
    # inheritance resolution is the pipeline's responsibility.
    assert cfg.spec.profiles["p"].groups["g"].order_streams_by is None
    assert cfg.spec.profiles["p"].groups["g"].members[0].order_streams_by is None


def test_group_null_clears_profile_value() -> None:
    """Group explicitly sets null; even if profile has quality, group clears it."""
    cfg = _make_config(_profile_dict(profile_osb="quality", group_osb=None))
    assert cfg.spec.profiles["p"].order_streams_by is OrderStreamsBy.QUALITY
    assert cfg.spec.profiles["p"].groups["g"].order_streams_by is None


def test_member_re_enables_when_group_cleared() -> None:
    """Member sets quality even though the group cleared the inherited value."""
    cfg = _make_config(_profile_dict(profile_osb="quality", group_osb=None, member_osb="quality"))
    assert cfg.spec.profiles["p"].groups["g"].order_streams_by is None
    assert cfg.spec.profiles["p"].groups["g"].members[0].order_streams_by is OrderStreamsBy.QUALITY
