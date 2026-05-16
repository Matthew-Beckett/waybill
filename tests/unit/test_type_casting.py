"""Unit tests for type-casting / coercion functions in src/types/config.py.

Tests exercise ``_to_transformer``, ``_to_validator``, and
``ConfigMember._to_matcher`` — the helpers that coerce raw YAML-loaded
dicts into typed dataclasses.  These are the first line of defence against
bad data silently flowing into the pipeline.

``src/types/config.py`` has no Django dependency, so no module stubs are
required.
"""

from __future__ import annotations

import pytest

from src.types.config import (
    CardinalOutputType,
    ConfigMatcher,
    ConfigMember,
    ConfigTransformer,
    ConfigValidator,
    MatcherAction,
    MatcherType,
    TransformerType,
    ValidatorAction,
    ValidatorOperator,
    ValidatorScope,
    ValidatorType,
    ConfigVariable,
    _to_transformer,
    _to_validator,
    _to_variable_dict,
)


class TestToTransformer:
    # --- identity pass-through ---

    def test_passthrough_when_already_config_transformer(self) -> None:
        original = ConfigTransformer(type=TransformerType.STRIP, prefix="UK: ")
        assert _to_transformer(original) is original

    # --- TransformerType enum coercion ---

    @pytest.mark.parametrize(
        "raw_dict, expected_type",
        [
            ({"type": "regex", "pattern": r"^NBS"}, TransformerType.REGEX),
            ({"type": "strip"}, TransformerType.STRIP),
            ({"type": "set", "value": "NBS One"}, TransformerType.SET),
            ({"type": "setMetadata", "name": "NBS One"}, TransformerType.SET_METADATA),
            (
                {"type": "convertCardinalNumbers", "outputType": "number"},
                TransformerType.CONVERT_CARDINAL_NUMBERS,
            ),
        ],
    )
    def test_type_string_coercion(self, raw_dict, expected_type) -> None:
        assert _to_transformer(raw_dict).type is expected_type

    def test_type_already_enum_passthrough(self) -> None:
        result = _to_transformer({"type": TransformerType.REGEX, "pattern": r".*"})
        assert result.type is TransformerType.REGEX

    def test_type_invalid_raises(self) -> None:
        with pytest.raises(ValueError):
            _to_transformer({"type": "unknownType"})

    # --- outputType coercion ---

    @pytest.mark.parametrize(
        "output_str, expected",
        [
            ("number", CardinalOutputType.NUMBER),
            ("word", CardinalOutputType.WORD),
        ],
    )
    def test_output_type_string_coercion(self, output_str, expected) -> None:
        result = _to_transformer(
            {"type": "convertCardinalNumbers", "outputType": output_str}
        )
        assert result.output_type is expected

    def test_output_type_empty_string_stays_empty(self) -> None:
        result = _to_transformer({"type": "convertCardinalNumbers", "outputType": ""})
        assert result.output_type == ""

    def test_output_type_absent_defaults_to_empty_string(self) -> None:
        result = _to_transformer({"type": "strip"})
        assert result.output_type == ""

    def test_output_type_already_enum_passthrough(self) -> None:
        result = _to_transformer(
            {"type": "convertCardinalNumbers", "outputType": CardinalOutputType.WORD}
        )
        assert result.output_type is CardinalOutputType.WORD

    def test_output_type_invalid_raises(self) -> None:
        with pytest.raises(ValueError):
            _to_transformer({"type": "convertCardinalNumbers", "outputType": "invalid"})

    # --- camelCase field mapping ---

    def test_logo_url_camel_case_mapped(self) -> None:
        result = _to_transformer(
            {"type": "setMetadata", "logoUrl": "https://example.com/logo.png"}
        )
        assert result.logo_url == "https://example.com/logo.png"

    def test_tvg_id_camel_case_mapped(self) -> None:
        result = _to_transformer({"type": "setMetadata", "tvgId": "bbc.one"})
        assert result.tvg_id == "bbc.one"

    # --- string coercion for scalar fields ---

    def test_action_coerced_to_str(self) -> None:
        result = _to_transformer({"type": "regex", "action": "replace"})
        assert result.action == "replace"

    def test_pattern_coerced_to_str(self) -> None:
        result = _to_transformer({"type": "regex", "pattern": r"^UK: "})
        assert result.pattern == "^UK: "

    def test_replacement_coerced_to_str(self) -> None:
        result = _to_transformer({"type": "regex", "replacement": "$1"})
        assert result.replacement == "$1"

    def test_prefix_coerced_to_str(self) -> None:
        result = _to_transformer({"type": "strip", "prefix": "UK: "})
        assert result.prefix == "UK: "

    def test_suffix_coerced_to_str(self) -> None:
        result = _to_transformer({"type": "strip", "suffix": " HD"})
        assert result.suffix == " HD"

    def test_value_coerced_to_str(self) -> None:
        result = _to_transformer({"type": "set", "value": "NBS One"})
        assert result.value == "NBS One"

    def test_name_coerced_to_str(self) -> None:
        result = _to_transformer({"type": "setMetadata", "name": "NBS One"})
        assert result.name == "NBS One"

    # --- field default ---

    def test_field_defaults_to_name(self) -> None:
        result = _to_transformer({"type": "strip", "prefix": "UK: "})
        assert result.field == "name"

    def test_field_override(self) -> None:
        result = _to_transformer({"type": "strip", "prefix": "UK: ", "field": "tvg_id"})
        assert result.field == "tvg_id"

    # --- extra keys ---

    def test_extra_keys_collected(self) -> None:
        result = _to_transformer(
            {"type": "strip", "prefix": "UK: ", "unknownKey": "some_value"}
        )
        assert result.extra == {"unknownKey": "some_value"}

    def test_known_keys_not_in_extra(self) -> None:
        result = _to_transformer(
            {"type": "regex", "pattern": r".*", "action": "replace", "replacement": ""}
        )
        assert "pattern" not in result.extra
        assert "action" not in result.extra
        assert "replacement" not in result.extra

    def test_empty_extra_when_no_unknown_keys(self) -> None:
        result = _to_transformer({"type": "strip", "prefix": "UK: "})
        assert result.extra == {}

    # --- missing optional fields default to empty string ---

    def test_absent_fields_default_to_empty_string(self) -> None:
        result = _to_transformer({"type": "strip"})
        assert result.prefix == ""
        assert result.suffix == ""
        assert result.pattern == ""
        assert result.replacement == ""
        assert result.value == ""
        assert result.name == ""
        assert result.logo_url == ""
        assert result.tvg_id == ""
        assert result.action == ""


class TestToValidator:
    # --- identity pass-through ---

    def test_passthrough_when_already_config_validator(self) -> None:
        original = ConfigValidator(type=ValidatorType.NON_EMPTY)
        assert _to_validator(original) is original

    # --- ValidatorType coercion ---

    @pytest.mark.parametrize(
        "raw_dict, expected_type",
        [
            ({"type": "count", "operator": "gt", "value": 0}, ValidatorType.COUNT),
            ({"type": "nonEmpty"}, ValidatorType.NON_EMPTY),
            ({"type": "regexMatch", "pattern": r".*"}, ValidatorType.REGEX_MATCH),
        ],
    )
    def test_type_string_coercion(self, raw_dict, expected_type) -> None:
        assert _to_validator(raw_dict).type is expected_type

    def test_type_already_enum_passthrough(self) -> None:
        result = _to_validator({"type": ValidatorType.COUNT, "value": 1})
        assert result.type is ValidatorType.COUNT

    def test_type_invalid_raises(self) -> None:
        with pytest.raises(ValueError):
            _to_validator({"type": "unknownValidator"})

    # --- ValidatorAction coercion ---

    @pytest.mark.parametrize(
        "action_str, expected",
        [
            ("warn", ValidatorAction.WARN),
            ("fail", ValidatorAction.FAIL),
        ],
    )
    def test_action_string_coercion(self, action_str, expected) -> None:
        result = _to_validator({"type": "nonEmpty", "action": action_str})
        assert result.action is expected

    def test_action_already_enum_passthrough(self) -> None:
        result = _to_validator({"type": "nonEmpty", "action": ValidatorAction.FAIL})
        assert result.action is ValidatorAction.FAIL

    def test_action_absent_defaults_to_warn(self) -> None:
        result = _to_validator({"type": "nonEmpty"})
        assert result.action is ValidatorAction.WARN

    def test_action_empty_string_defaults_to_warn(self) -> None:
        result = _to_validator({"type": "nonEmpty", "action": ""})
        assert result.action is ValidatorAction.WARN

    def test_action_invalid_raises(self) -> None:
        with pytest.raises(ValueError):
            _to_validator({"type": "nonEmpty", "action": "explode"})

    # --- ValidatorOperator coercion ---

    @pytest.mark.parametrize(
        "raw, expected",
        [
            ("gt", ValidatorOperator.GT),
            ("gte", ValidatorOperator.GTE),
            ("lt", ValidatorOperator.LT),
            ("lte", ValidatorOperator.LTE),
            ("eq", ValidatorOperator.EQ),
            ("neq", ValidatorOperator.NEQ),
        ],
    )
    def test_operator_string_coercion(
        self, raw: str, expected: ValidatorOperator
    ) -> None:
        result = _to_validator({"type": "count", "operator": raw, "value": 1})
        assert result.operator is expected

    def test_operator_already_enum_passthrough(self) -> None:
        result = _to_validator(
            {"type": "count", "operator": ValidatorOperator.GTE, "value": 2}
        )
        assert result.operator is ValidatorOperator.GTE

    def test_operator_absent_defaults_to_gt(self) -> None:
        result = _to_validator({"type": "count", "value": 1})
        assert result.operator is ValidatorOperator.GT

    def test_operator_empty_string_defaults_to_gt(self) -> None:
        result = _to_validator({"type": "count", "operator": "", "value": 1})
        assert result.operator is ValidatorOperator.GT

    def test_operator_invalid_raises(self) -> None:
        with pytest.raises(ValueError):
            _to_validator({"type": "count", "operator": "between", "value": 1})

    # --- value int casting ---

    def test_value_int_passthrough(self) -> None:
        result = _to_validator({"type": "count", "value": 5})
        assert result.value == 5

    def test_value_string_coerced_to_int(self) -> None:
        result = _to_validator({"type": "count", "value": "5"})
        assert result.value == 5

    def test_value_float_truncated_to_int(self) -> None:
        result = _to_validator({"type": "count", "value": 5.9})
        assert result.value == 5

    def test_value_none_defaults_to_zero(self) -> None:
        result = _to_validator({"type": "count", "value": None})
        assert result.value == 0

    def test_value_non_numeric_string_defaults_to_zero(self) -> None:
        result = _to_validator({"type": "count", "value": "not_a_number"})
        assert result.value == 0

    def test_value_absent_defaults_to_zero(self) -> None:
        result = _to_validator({"type": "count"})
        assert result.value == 0

    def test_value_zero(self) -> None:
        result = _to_validator({"type": "count", "value": 0})
        assert result.value == 0

    def test_value_large_int(self) -> None:
        result = _to_validator({"type": "count", "value": 10000})
        assert result.value == 10000

    @pytest.mark.parametrize(
        ("validator_type", "raw_scope", "expected"),
        [
            ("count", "channel", ValidatorScope.CHANNEL),
            ("count", ValidatorScope.MEMBER, ValidatorScope.MEMBER),
            ("regexMatch", "stream", ValidatorScope.STREAM),
            ("nonEmpty", ValidatorScope.CHANNEL, ValidatorScope.CHANNEL),
        ],
    )
    def test_scope_coercion(
        self, validator_type: str, raw_scope: object, expected: ValidatorScope
    ) -> None:
        result = _to_validator({"type": validator_type, "scope": raw_scope})
        assert result.scope is expected

    @pytest.mark.parametrize("validator_type", ["count", "nonEmpty"])
    def test_scope_absent_defaults_to_none(self, validator_type: str) -> None:
        result = _to_validator({"type": validator_type})
        assert result.scope is None

    def test_scope_empty_string_defaults_to_none(self) -> None:
        result = _to_validator({"type": "count", "scope": ""})
        assert result.scope is None

    # --- pattern and field ---

    def test_pattern_preserved(self) -> None:
        result = _to_validator({"type": "regexMatch", "pattern": r"^NBS"})
        assert result.pattern == "^NBS"

    def test_pattern_absent_defaults_to_empty_string(self) -> None:
        result = _to_validator({"type": "nonEmpty"})
        assert result.pattern == ""

    def test_field_preserved(self) -> None:
        result = _to_validator({"type": "nonEmpty", "field": "tvg_id"})
        assert result.field == "tvg_id"

    def test_field_absent_defaults_to_name(self) -> None:
        result = _to_validator({"type": "nonEmpty"})
        assert result.field == "name"

    def test_scope_invalid_raises(self) -> None:
        with pytest.raises(ValueError):
            _to_validator({"type": "count", "scope": "everywhere"})


class TestConfigMemberToMatcher:
    """Drive _to_matcher via ConfigMember construction so __post_init__ runs."""

    def _member_with_matcher(self, matcher_dict: dict) -> ConfigMember:
        return ConfigMember(name="test", matchers=[matcher_dict])

    # --- identity pass-through ---

    def test_passthrough_when_already_config_matcher(self) -> None:
        existing = ConfigMatcher(type=MatcherType.REGEX, pattern=r"^NBS")
        member = ConfigMember(name="test", matchers=[existing])
        assert member.matchers[0] is existing

    # --- MatcherType coercion ---

    @pytest.mark.parametrize(
        "raw_dict, expected_type",
        [
            ({"type": "regex", "pattern": r"^NBS"}, MatcherType.REGEX),
            ({"type": "hasPrefix", "prefixes": ["NBS"]}, MatcherType.HAS_PREFIX),
            ({"type": "containsAny", "substrings": ["NBS"]}, MatcherType.CONTAINS_ANY),
            ({"type": "exactMatch", "values": ["NBS One"]}, MatcherType.EXACT_MATCH),
        ],
    )
    def test_type_string_coercion(self, raw_dict, expected_type) -> None:
        member = self._member_with_matcher(raw_dict)
        assert member.matchers[0].type is expected_type

    def test_type_already_enum_passthrough(self) -> None:
        member = self._member_with_matcher(
            {"type": MatcherType.HAS_PREFIX, "prefixes": ["VTN"]}
        )
        assert member.matchers[0].type is MatcherType.HAS_PREFIX

    def test_type_invalid_raises(self) -> None:
        with pytest.raises(ValueError):
            self._member_with_matcher({"type": "unknownMatcher"})

    # --- MatcherAction coercion ---

    @pytest.mark.parametrize(
        "action_str, expected",
        [
            ("keep", MatcherAction.KEEP),
            ("drop", MatcherAction.DROP),
        ],
    )
    def test_action_string_coercion(self, action_str, expected) -> None:
        member = self._member_with_matcher(
            {"type": "regex", "action": action_str, "pattern": r".*"}
        )
        assert member.matchers[0].action is expected

    def test_action_already_enum_passthrough(self) -> None:
        member = self._member_with_matcher(
            {"type": "regex", "action": MatcherAction.DROP, "pattern": r".*"}
        )
        assert member.matchers[0].action is MatcherAction.DROP

    def test_action_absent_defaults_to_keep(self) -> None:
        member = self._member_with_matcher({"type": "regex", "pattern": r".*"})
        assert member.matchers[0].action is MatcherAction.KEEP

    def test_action_empty_string_defaults_to_keep(self) -> None:
        member = self._member_with_matcher(
            {"type": "regex", "action": "", "pattern": r".*"}
        )
        assert member.matchers[0].action is MatcherAction.KEEP

    def test_action_invalid_raises(self) -> None:
        with pytest.raises(ValueError):
            self._member_with_matcher(
                {"type": "regex", "action": "ignore", "pattern": r".*"}
            )

    # --- list fields coerced to list[str] ---

    def test_prefixes_coerced_to_str_list(self) -> None:
        member = self._member_with_matcher(
            {"type": "hasPrefix", "prefixes": ["NBS", "VTN"]}
        )
        assert member.matchers[0].prefixes == ["NBS", "VTN"]

    def test_substrings_coerced_to_str_list(self) -> None:
        member = self._member_with_matcher(
            {"type": "containsAny", "substrings": ["News", "Sport"]}
        )
        assert member.matchers[0].substrings == ["News", "Sport"]

    def test_values_coerced_to_str_list(self) -> None:
        member = self._member_with_matcher(
            {"type": "exactMatch", "values": ["NBS One", "NBS Two"]}
        )
        assert member.matchers[0].values == ["NBS One", "NBS Two"]

    def test_prefixes_non_list_yields_empty_list(self) -> None:
        member = self._member_with_matcher({"type": "hasPrefix", "prefixes": "NBS"})
        assert member.matchers[0].prefixes == []

    def test_substrings_non_list_yields_empty_list(self) -> None:
        member = self._member_with_matcher(
            {"type": "containsAny", "substrings": "News"}
        )
        assert member.matchers[0].substrings == []

    def test_values_non_list_yields_empty_list(self) -> None:
        member = self._member_with_matcher({"type": "exactMatch", "values": "NBS One"})
        assert member.matchers[0].values == []

    # --- caseSensitive bool coercion ---

    def test_case_sensitive_true(self) -> None:
        member = self._member_with_matcher(
            {"type": "regex", "caseSensitive": True, "pattern": r".*"}
        )
        assert member.matchers[0].case_sensitive is True

    def test_case_sensitive_false(self) -> None:
        member = self._member_with_matcher(
            {"type": "regex", "caseSensitive": False, "pattern": r".*"}
        )
        assert member.matchers[0].case_sensitive is False

    def test_case_sensitive_absent_defaults_to_false(self) -> None:
        member = self._member_with_matcher({"type": "regex", "pattern": r".*"})
        assert member.matchers[0].case_sensitive is False

    def test_case_sensitive_truthy_int(self) -> None:
        member = self._member_with_matcher(
            {"type": "regex", "caseSensitive": 1, "pattern": r".*"}
        )
        assert member.matchers[0].case_sensitive is True

    # --- field ---

    def test_field_preserved(self) -> None:
        member = self._member_with_matcher(
            {"type": "regex", "pattern": r".*", "field": "tvg_id"}
        )
        assert member.matchers[0].field == "tvg_id"

    def test_field_absent_defaults_to_name(self) -> None:
        member = self._member_with_matcher({"type": "regex", "pattern": r".*"})
        assert member.matchers[0].field == "name"

    # --- pattern ---

    def test_pattern_preserved(self) -> None:
        member = self._member_with_matcher({"type": "regex", "pattern": r"^NBS\s"})
        assert member.matchers[0].pattern == r"^NBS\s"

    def test_pattern_absent_defaults_to_empty_string(self) -> None:
        member = self._member_with_matcher({"type": "hasPrefix", "prefixes": ["NBS"]})
        assert member.matchers[0].pattern == ""


class TestConfigMemberPostInit:
    def test_matchers_dicts_coerced_on_construction(self) -> None:
        member = ConfigMember(
            name="test",
            matchers=[{"type": "regex", "pattern": r"^NBS"}],
        )
        assert len(member.matchers) == 1
        assert isinstance(member.matchers[0], ConfigMatcher)
        assert member.matchers[0].type is MatcherType.REGEX

    def test_transformers_dicts_coerced_on_construction(self) -> None:
        member = ConfigMember(
            name="test",
            transformers=[{"type": "strip", "prefix": "UK: "}],
        )
        assert len(member.transformers) == 1
        assert isinstance(member.transformers[0], ConfigTransformer)
        assert member.transformers[0].type is TransformerType.STRIP

    def test_validators_dicts_coerced_on_construction(self) -> None:
        member = ConfigMember(
            name="test",
            validators=[{"type": "nonEmpty", "field": "tvg_id"}],
        )
        assert len(member.validators) == 1
        assert isinstance(member.validators[0], ConfigValidator)
        assert member.validators[0].type is ValidatorType.NON_EMPTY

    def test_mixed_lists_with_existing_instances(self) -> None:
        existing_matcher = ConfigMatcher(type=MatcherType.REGEX, pattern=r".*")
        existing_validator = ConfigValidator(type=ValidatorType.COUNT, value=1)
        member = ConfigMember(
            name="test",
            matchers=[existing_matcher],
            validators=[existing_validator],
        )
        assert member.matchers[0] is existing_matcher
        assert member.validators[0] is existing_validator

    def test_multiple_matchers_all_coerced(self) -> None:
        member = ConfigMember(
            name="test",
            matchers=[
                {"type": "regex", "pattern": r"^NBS"},
                {"type": "hasPrefix", "prefixes": ["VTN"]},
            ],
        )
        assert len(member.matchers) == 2
        assert member.matchers[0].type is MatcherType.REGEX
        assert member.matchers[1].type is MatcherType.HAS_PREFIX

    def test_empty_lists_remain_empty(self) -> None:
        member = ConfigMember(name="test")
        assert member.matchers == []
        assert member.transformers == []
        assert member.validators == []


class TestConfigMatcherPostInit:
    def test_transformer_dict_coerced(self) -> None:
        matcher = ConfigMatcher(
            type=MatcherType.REGEX,
            pattern=r"^BB",
            transformers=[{"type": "strip", "prefix": "UK: "}],
        )
        assert len(matcher.transformers) == 1
        assert isinstance(matcher.transformers[0], ConfigTransformer)
        assert matcher.transformers[0].type is TransformerType.STRIP

    def test_existing_transformer_instance_passthrough(self) -> None:
        t = ConfigTransformer(type=TransformerType.STRIP, prefix="UK: ")
        matcher = ConfigMatcher(type=MatcherType.REGEX, pattern=r".*", transformers=[t])
        assert matcher.transformers[0] is t

    def test_empty_transformers_list(self) -> None:
        matcher = ConfigMatcher(type=MatcherType.REGEX, pattern=r".*")
        assert matcher.transformers == []


class TestToVariableDict:
    def test_passthrough_config_variable_instance(self) -> None:
        var = ConfigVariable(value="Arena", mutable=False)
        result = _to_variable_dict({"brand": var})
        assert result["brand"] is var

    def test_dict_with_value_and_mutable(self) -> None:
        result = _to_variable_dict({"brand": {"value": "Arena", "mutable": False}})
        assert result["brand"].value == "Arena"
        assert result["brand"].mutable is False

    def test_dict_with_value_only_defaults_mutable_true(self) -> None:
        result = _to_variable_dict({"suffix": {"value": " HD"}})
        assert result["suffix"].value == " HD"
        assert result["suffix"].mutable is True

    def test_scalar_shorthand_creates_mutable_variable(self) -> None:
        result = _to_variable_dict({"network": "NBS"})
        assert result["network"].value == "NBS"
        assert result["network"].mutable is True

    def test_empty_dict_returns_empty(self) -> None:
        result = _to_variable_dict({})
        assert result == {}

    def test_non_dict_input_returns_empty(self) -> None:
        assert _to_variable_dict(None) == {}  # type: ignore[arg-type]
        assert _to_variable_dict("string") == {}  # type: ignore[arg-type]
        assert _to_variable_dict(42) == {}  # type: ignore[arg-type]

    def test_multiple_variables(self) -> None:
        result = _to_variable_dict(
            {"brand": "Arena", "quality": {"value": "HD", "mutable": False}}
        )
        assert result["brand"].value == "Arena"
        assert result["brand"].mutable is True
        assert result["quality"].value == "HD"
        assert result["quality"].mutable is False


class TestConfigMemberVariablesCoercion:
    def test_scalar_variables_coerced(self) -> None:
        member = ConfigMember(
            name="test",
            variables={"brand": "Arena"},
        )
        assert isinstance(member.variables["brand"], ConfigVariable)
        assert member.variables["brand"].value == "Arena"

    def test_dict_variables_coerced(self) -> None:
        member = ConfigMember(
            name="test",
            variables={"network": {"value": "NBS", "mutable": False}},
        )
        assert member.variables["network"].mutable is False

    def test_existing_config_variable_passthrough(self) -> None:
        var = ConfigVariable(value="Arena", mutable=True)
        member = ConfigMember(name="test", variables={"brand": var})
        assert member.variables["brand"] is var

    def test_empty_variables_default(self) -> None:
        member = ConfigMember(name="test")
        assert member.variables == {}
