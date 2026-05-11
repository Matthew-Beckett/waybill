from dataclasses import dataclass, field
from enum import Enum as Enum
from typing import Any, Mapping, cast


SUPPORTED_CONFIG_KIND = "WaybillConfig"
SUPPORTED_CONFIG_VERSION = "v1alpha1"


def _empty_str_list() -> list[str]:
    return []


def _empty_str_any_dict() -> dict[str, Any]:
    return {}


def _empty_matchers() -> list["ConfigMatcher"]:
    return []


def _empty_transformers() -> list["ConfigTransformer"]:
    return []


def _empty_members() -> list["ConfigMember"]:
    return []


def _empty_str_group_dict() -> dict[str, "ConfigGroup"]:
    return {}


def _empty_str_profile_dict() -> dict[str, "ConfigProfile"]:
    return {}


class MatcherType(Enum):
    REGEX = "regex"
    HAS_PREFIX = "hasPrefix"
    CONTAINS_ANY = "containsAny"
    EXACT_MATCH = "exactMatch"


class MatcherAction(Enum):
    KEEP = "keep"
    DROP = "drop"


class TransformerType(Enum):
    CONVERT_CARDINAL_NUMBERS = "convertCardinalNumbers"
    REGEX = "regex"
    STRIP = "strip"
    SET = "set"


class CardinalOutputType(Enum):
    NUMBER = "number"
    WORD = "word"


class OrderStreamsBy(Enum):
    QUALITY = "quality"


@dataclass(frozen=True)
class ConfigMetadata:
    name: str
    description: str = ""


@dataclass(frozen=True)
class ConfigTransformer:
    type: TransformerType
    action: str = ""
    output_type: CardinalOutputType | str = ""
    pattern: str = ""
    replacement: str = ""
    prefix: str = ""
    suffix: str = ""
    value: str = ""
    extra: dict[str, Any] = field(default_factory=_empty_str_any_dict)
    # NOTE: `field` must be last — it shadows the dataclasses.field() import after this line
    field: str = "name"


def _to_transformer(item: "ConfigTransformer | Mapping[str, Any]") -> "ConfigTransformer":
    """Coerce a raw mapping (from YAML) or an existing ConfigTransformer into a ConfigTransformer."""
    if isinstance(item, ConfigTransformer):
        return item

    raw_type = item.get("type", "")
    transformer_type = raw_type if isinstance(raw_type, TransformerType) else TransformerType(str(raw_type))

    raw_output_type = item.get("outputType", "")
    output_type: CardinalOutputType | str
    if isinstance(raw_output_type, CardinalOutputType):
        output_type = raw_output_type
    elif isinstance(raw_output_type, str) and raw_output_type:
        output_type = CardinalOutputType(raw_output_type)
    else:
        output_type = ""

    known_keys = {
        "type",
        "action",
        "outputType",
        "field",
        "pattern",
        "replacement",
        "prefix",
        "suffix",
        "value",
    }
    extra = {str(key): value for key, value in item.items() if key not in known_keys}

    return ConfigTransformer(
        type=transformer_type,
        action=str(item.get("action", "")),
        output_type=output_type,
        pattern=str(item.get("pattern", "")),
        replacement=str(item.get("replacement", "")),
        prefix=str(item.get("prefix", "")),
        suffix=str(item.get("suffix", "")),
        value=str(item.get("value", "")),
        extra=extra,
        field=str(item.get("field", "name")),
    )


@dataclass
class ConfigMatcher:
    type: MatcherType
    action: MatcherAction = MatcherAction.KEEP
    pattern: str = ""
    prefixes: list[str] = field(default_factory=_empty_str_list)
    substrings: list[str] = field(default_factory=_empty_str_list)
    values: list[str] = field(default_factory=_empty_str_list)
    case_sensitive: bool = False
    transformers: list[ConfigTransformer] = field(default_factory=_empty_transformers)
    # NOTE: `field` must be last — it shadows the dataclasses.field() import after this line
    field: str = "name"

    def __post_init__(self) -> None:
        self.transformers = [_to_transformer(item) for item in self.transformers]


def _to_order_streams_by(raw: Any) -> "OrderStreamsBy | None":
    """Coerce a raw YAML value to OrderStreamsBy, or None if absent."""
    if raw is None or raw == "":
        return None
    if isinstance(raw, OrderStreamsBy):
        return raw
    return OrderStreamsBy(str(raw))


@dataclass
class ConfigMember:
    name: str
    matchers: list[ConfigMatcher] = field(default_factory=_empty_matchers)
    transformers: list[ConfigTransformer] = field(default_factory=_empty_transformers)
    stream_profile: str | None = None
    order_streams_by: OrderStreamsBy | None = None

    def __post_init__(self):
        self.matchers = [self._to_matcher(item) for item in self.matchers]
        self.transformers = [_to_transformer(item) for item in self.transformers]

    @staticmethod
    def _to_matcher(item: ConfigMatcher | Mapping[str, Any]) -> ConfigMatcher:
        if isinstance(item, ConfigMatcher):
            return item

        raw_type = item.get("type", MatcherType.REGEX)
        matcher_type = raw_type if isinstance(raw_type, MatcherType) else MatcherType(str(raw_type))

        raw_action = item.get("action", MatcherAction.KEEP)
        matcher_action: MatcherAction
        if isinstance(raw_action, MatcherAction):
            matcher_action = raw_action
        else:
            matcher_action = MatcherAction(str(raw_action)) if raw_action else MatcherAction.KEEP

        raw_prefixes = item.get("prefixes", [])
        prefixes = [str(p) for p in cast(list[Any], raw_prefixes)] if isinstance(raw_prefixes, list) else _empty_str_list()

        raw_substrings = item.get("substrings", [])
        substrings = [str(s) for s in cast(list[Any], raw_substrings)] if isinstance(raw_substrings, list) else _empty_str_list()

        raw_values = item.get("values", [])
        values = [str(v) for v in cast(list[Any], raw_values)] if isinstance(raw_values, list) else _empty_str_list()

        case_sensitive = bool(item.get("caseSensitive", False))

        raw_transformers = item.get("transformers", [])
        transformers = cast(list[ConfigTransformer], raw_transformers) if isinstance(raw_transformers, list) else _empty_transformers()

        return ConfigMatcher(
            type=matcher_type,
            action=matcher_action,
            pattern=str(item.get("pattern", "")),
            prefixes=prefixes,
            substrings=substrings,
            values=values,
            case_sensitive=case_sensitive,
            transformers=transformers,
            field=str(item.get("field", "name")),
        )


@dataclass
class ConfigGroup:
    name: str
    members: list[ConfigMember] = field(default_factory=_empty_members)
    stream_profile: str | None = None
    order_streams_by: OrderStreamsBy | None = None

    def __post_init__(self):
        self.members = [self._to_member(item) for item in self.members]

    @staticmethod
    def _to_member(item: ConfigMember | Mapping[str, Any]) -> ConfigMember:
        if isinstance(item, ConfigMember):
            return item

        raw_matchers = item.get("matchers", [])
        raw_transformers = item.get("transformers", [])

        matchers = cast(list[ConfigMatcher], raw_matchers) if isinstance(raw_matchers, list) else _empty_matchers()
        transformers = cast(list[ConfigTransformer], raw_transformers) if isinstance(raw_transformers, list) else _empty_transformers()

        return ConfigMember(
            name=str(item.get("name", "")),
            matchers=matchers,
            transformers=transformers,
            stream_profile=item.get("streamProfile") or None,
            order_streams_by=_to_order_streams_by(item.get("orderStreamsBy")),
        )


@dataclass
class ConfigProfile:
    name: str = ""
    groups: dict[str, ConfigGroup] = field(default_factory=_empty_str_group_dict)
    stream_profile: str | None = None
    order_streams_by: OrderStreamsBy | None = None

    def __post_init__(self):
        self.groups = {name: self._to_group(value) for name, value in self.groups.items()}

    @staticmethod
    def _to_group(item: ConfigGroup | Mapping[str, Any]) -> ConfigGroup:
        if isinstance(item, ConfigGroup):
            return item

        raw_members = item.get("members", [])
        members = cast(list[ConfigMember], raw_members) if isinstance(raw_members, list) else _empty_members()

        return ConfigGroup(
            name=str(item.get("name", "")),
            members=members,
            stream_profile=item.get("streamProfile") or None,
            order_streams_by=_to_order_streams_by(item.get("orderStreamsBy")),
        )


@dataclass
class ConfigSpec:
    profiles: dict[str, ConfigProfile] = field(default_factory=_empty_str_profile_dict)

    def __post_init__(self):
        self.profiles = {name: self._to_profile(value) for name, value in self.profiles.items()}

    @staticmethod
    def _to_profile(item: ConfigProfile | Mapping[str, Any]) -> ConfigProfile:
        if isinstance(item, ConfigProfile):
            return item

        raw_groups = item.get("groups", {})
        groups = cast(dict[str, ConfigGroup], raw_groups) if isinstance(raw_groups, dict) else _empty_str_group_dict()

        return ConfigProfile(
            name=str(item.get("name", "")),
            groups=groups,
            stream_profile=item.get("streamProfile") or None,
            order_streams_by=_to_order_streams_by(item.get("orderStreamsBy")),
        )


@dataclass
class WaybillConfig:
    kind: str
    version: str
    metadata: ConfigMetadata
    spec: ConfigSpec = field(default_factory=ConfigSpec)

    def __post_init__(self):
        self.metadata = self._to_metadata(self.metadata)
        self.spec = self._to_spec(self.spec)
        if self.kind != SUPPORTED_CONFIG_KIND:
            raise ValueError(
                f"Unsupported config kind {self.kind!r}; expected {SUPPORTED_CONFIG_KIND!r}"
            )
        if self.version != SUPPORTED_CONFIG_VERSION:
            raise ValueError(
                f"Unsupported config version {self.version!r}; expected {SUPPORTED_CONFIG_VERSION!r}"
            )
        if not self.metadata.name.strip():
            raise ValueError("metadata.name must be a non-empty string")

    @staticmethod
    def _to_metadata(item: ConfigMetadata | Mapping[str, Any]) -> ConfigMetadata:
        if isinstance(item, ConfigMetadata):
            return item

        return ConfigMetadata(
            name=str(item.get("name", "")),
            description=str(item.get("description", "")),
        )

    @staticmethod
    def _to_spec(item: ConfigSpec | Mapping[str, Any]) -> ConfigSpec:
        if isinstance(item, ConfigSpec):
            return item

        raw_profiles = item.get("profiles", {})
        profiles = cast(dict[str, ConfigProfile], raw_profiles) if isinstance(raw_profiles, dict) else _empty_str_profile_dict()

        return ConfigSpec(profiles=profiles)