"""Unit tests for the validators package."""

from __future__ import annotations

import sys
import types
from types import SimpleNamespace

import pytest


_channels_models = types.ModuleType("apps.channels.models")
_channels_models.Stream = object  # type: ignore[attr-defined]

for _mod_name, _mod in (
    ("apps", types.ModuleType("apps")),
    ("apps.channels", types.ModuleType("apps.channels")),
    ("apps.channels.models", _channels_models),
):
    if _mod_name not in sys.modules:
        sys.modules[_mod_name] = _mod

from src.types.config import (  # noqa: E402
    ConfigValidator,
    ValidatorOperator,
    ValidatorScope,
    ValidatorType,
)
from src.types.plan import ChannelPlan, MemberPlan, StreamRecord  # noqa: E402
from src.validators import build_validator  # noqa: E402
from src.validators.base import (  # noqa: E402
    WaybillChannelValidatorBase,
    WaybillMemberValidatorBase,
    WaybillStreamValidatorBase,
)
from src.validators.count import (  # noqa: E402
    WaybillValidatorCountChannel,
    WaybillValidatorCountMember,
)
from src.validators.non_empty import (  # noqa: E402
    WaybillValidatorNonEmpty,
    WaybillValidatorNonEmptyChannel,
)
from src.validators.regex import (  # noqa: E402
    WaybillValidatorRegexMatch,
    WaybillValidatorRegexMatchChannel,
)


def _stream(name: str = "Channel 1", tvg_id: str = "ch1.demo") -> SimpleNamespace:
    return SimpleNamespace(name=name, tvg_id=tvg_id, logo_url="")


def _stream_record(id: int = 1) -> StreamRecord:
    return StreamRecord(
        id=id,
        original_name=f"Channel {id}",
        transformed_name="Channel",
    )


def _channel(count: int = 1, name: str = "Channel") -> ChannelPlan:
    return ChannelPlan(name=name, streams=[_stream_record(i) for i in range(count)])


def _member(channel_count: int = 1) -> MemberPlan:
    return MemberPlan(
        member_name="Member",
        channels=[ChannelPlan(name=f"Channel {i}") for i in range(channel_count)],
    )


class TestWaybillValidatorNonEmpty:
    @pytest.mark.parametrize(
        ("field", "stream_kwargs", "expected"),
        [
            ("name", {"name": "BBC One"}, True),
            ("name", {"name": ""}, False),
            ("tvg_id", {"tvg_id": "bbc.one"}, True),
            ("tvg_id", {"tvg_id": ""}, False),
        ],
    )
    def test_stream_scope_validation(
        self,
        field: str,
        stream_kwargs: dict[str, str],
        expected: bool,
    ) -> None:
        validator = WaybillValidatorNonEmpty(action="warn", field=field)
        assert validator.validate(_stream(**stream_kwargs)) is expected

    def test_action_is_preserved(self) -> None:
        validator = WaybillValidatorNonEmpty(action="fail", field="name")
        assert validator.action == "fail"

    def test_describe_includes_field_and_action(self) -> None:
        desc = WaybillValidatorNonEmpty(action="warn", field="tvg_id").describe()
        assert "tvg_id" in desc
        assert "warn" in desc

    def test_is_stream_validator(self) -> None:
        assert isinstance(
            WaybillValidatorNonEmpty(action="warn", field="name"),
            WaybillStreamValidatorBase,
        )

    @pytest.mark.parametrize(
        ("field", "channel_kwargs", "expected"),
        [
            ("name", {"name": "BBC One"}, True),
            ("name", {"name": ""}, False),
            ("tvg_id", {"epg_id": "bbc.one"}, True),
            ("tvg_id", {"epg_id": ""}, False),
        ],
    )
    def test_channel_scope_validation(
        self,
        field: str,
        channel_kwargs: dict[str, str],
        expected: bool,
    ) -> None:
        validator = WaybillValidatorNonEmptyChannel(action="warn", field=field)
        assert (
            validator.validate(ChannelPlan(**{"name": "Channel", **channel_kwargs}))
            is expected
        )

    def test_channel_description_mentions_scope(self) -> None:
        desc = WaybillValidatorNonEmptyChannel(action="warn", field="tvg_id").describe()
        assert 'scope="channel"' in desc
        assert "tvg_id" in desc

    def test_channel_validator_base(self) -> None:
        assert isinstance(
            WaybillValidatorNonEmptyChannel(action="warn", field="name"),
            WaybillChannelValidatorBase,
        )


class TestWaybillValidatorRegexMatch:
    @pytest.mark.parametrize(
        ("field", "pattern", "stream_kwargs", "expected"),
        [
            ("name", r"^BBC", {"name": "BBC One"}, True),
            ("name", r"^BBC", {"name": "ITV 1"}, False),
            ("tvg_id", r"\.demo$", {"tvg_id": "bbc.demo"}, True),
            ("tvg_id", r"\.demo$", {"tvg_id": "bbc.live"}, False),
        ],
    )
    def test_stream_scope_validation(
        self,
        field: str,
        pattern: str,
        stream_kwargs: dict[str, str],
        expected: bool,
    ) -> None:
        validator = WaybillValidatorRegexMatch(
            pattern=pattern,
            action="warn",
            field=field,
        )
        assert validator.validate(_stream(**stream_kwargs)) is expected

    def test_action_is_preserved(self) -> None:
        assert (
            WaybillValidatorRegexMatch(
                pattern=r".*", action="fail", field="name"
            ).action
            == "fail"
        )

    def test_describe_includes_pattern_and_action(self) -> None:
        desc = WaybillValidatorRegexMatch(
            pattern=r"^NBS",
            action="warn",
            field="name",
        ).describe()
        assert "NBS" in desc
        assert "warn" in desc

    def test_is_stream_validator(self) -> None:
        assert isinstance(
            WaybillValidatorRegexMatch(pattern=r".*", action="warn", field="name"),
            WaybillStreamValidatorBase,
        )

    @pytest.mark.parametrize(
        ("field", "pattern", "channel_kwargs", "expected"),
        [
            ("name", r"^BBC", {"name": "BBC One"}, True),
            ("name", r"^BBC", {"name": "ITV 1"}, False),
            ("tvg_id", r"\.demo$", {"epg_id": "bbc.demo"}, True),
            ("tvg_id", r"\.demo$", {"epg_id": "bbc.live"}, False),
        ],
    )
    def test_channel_scope_validation(
        self,
        field: str,
        pattern: str,
        channel_kwargs: dict[str, str],
        expected: bool,
    ) -> None:
        validator = WaybillValidatorRegexMatchChannel(
            pattern=pattern,
            action="warn",
            field=field,
        )
        assert (
            validator.validate(ChannelPlan(**{"name": "Channel", **channel_kwargs}))
            is expected
        )

    def test_channel_description_mentions_scope(self) -> None:
        desc = WaybillValidatorRegexMatchChannel(
            pattern=r"^NBS",
            action="warn",
            field="name",
        ).describe()
        assert 'scope="channel"' in desc
        assert "NBS" in desc

    def test_channel_validator_base(self) -> None:
        assert isinstance(
            WaybillValidatorRegexMatchChannel(
                pattern=r".*",
                action="warn",
                field="name",
            ),
            WaybillChannelValidatorBase,
        )


class TestWaybillValidatorCountChannel:
    @pytest.mark.parametrize(
        ("operator", "value", "stream_count", "expected"),
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
            ("gt", 0, 0, False),
            ("eq", 0, 0, True),
        ],
    )
    def test_validate(
        self, operator: str, value: int, stream_count: int, expected: bool
    ) -> None:
        assert (
            WaybillValidatorCountChannel(operator, value).validate(
                _channel(stream_count)
            )
            is expected
        )

    def test_action_is_preserved(self) -> None:
        assert WaybillValidatorCountChannel("gt", 0, action="fail").action == "fail"

    def test_describe_includes_scope_value_and_action(self) -> None:
        desc = WaybillValidatorCountChannel("gt", 0, action="warn").describe()
        assert 'scope="channel"' in desc
        assert "0" in desc
        assert "warn" in desc

    def test_is_channel_validator(self) -> None:
        assert isinstance(
            WaybillValidatorCountChannel("gt", 0),
            WaybillChannelValidatorBase,
        )


class TestWaybillValidatorCountMember:
    @pytest.mark.parametrize(
        ("operator", "value", "channel_count", "expected"),
        [
            ("gt", 0, 1, True),
            ("gt", 1, 1, False),
            ("eq", 2, 2, True),
            ("eq", 2, 3, False),
            ("gt", 0, 0, False),
            ("eq", 0, 0, True),
        ],
    )
    def test_validate(
        self,
        operator: str,
        value: int,
        channel_count: int,
        expected: bool,
    ) -> None:
        assert (
            WaybillValidatorCountMember(operator, value).validate(
                _member(channel_count)
            )
            is expected
        )

    def test_is_member_validator(self) -> None:
        assert isinstance(
            WaybillValidatorCountMember("gt", 0), WaybillMemberValidatorBase
        )


class TestBuildValidator:
    @pytest.mark.parametrize(
        ("cfg", "expected_cls"),
        [
            (
                ConfigValidator(type=ValidatorType.COUNT, value=1),
                WaybillValidatorCountMember,
            ),
            (
                ConfigValidator(
                    type=ValidatorType.COUNT,
                    operator=ValidatorOperator.GT,
                    value=0,
                    scope=ValidatorScope.CHANNEL,
                ),
                WaybillValidatorCountChannel,
            ),
            (
                ConfigValidator(
                    type=ValidatorType.NON_EMPTY,
                    field="tvg_id",
                    scope=ValidatorScope.CHANNEL,
                ),
                WaybillValidatorNonEmptyChannel,
            ),
            (
                ConfigValidator(
                    type=ValidatorType.REGEX_MATCH,
                    pattern=r"^NBS",
                    field="name",
                    scope=ValidatorScope.CHANNEL,
                ),
                WaybillValidatorRegexMatchChannel,
            ),
        ],
    )
    def test_build_validator_respects_scope(
        self,
        cfg: ConfigValidator,
        expected_cls: type,
    ) -> None:
        assert isinstance(build_validator(cfg), expected_cls)
