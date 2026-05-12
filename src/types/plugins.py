from dataclasses import dataclass, field
from enum import Enum as Enum
from typing import Any, Mapping, cast
from .config import ConfigMetadata, ConfigSpec, WaybillConfig


def _empty_any_list() -> list[Any]:
    return []


def _empty_str_any_dict() -> dict[str, Any]:
    return {}


def _empty_str_list() -> list[str]:
    return []


class PluginFieldType(Enum):
    STRING = "string"
    NUMBER = "number"
    BOOLEAN = "boolean"
    SELECT = "select"
    TEXT = "text"
    INFO = "info"


@dataclass(frozen=True)
class PluginField:
    id: str
    label: str
    type: PluginFieldType
    default: object = None
    description: str = ""
    options: list[Any] = field(default_factory=_empty_any_list)


@dataclass(frozen=True)
class PluginAction:
    id: str
    label: str
    description: str = ""
    confirm: dict[str, Any] = field(default_factory=_empty_str_any_dict)
    button_label: str = ""
    button_variant: str = ""
    button_color: str = ""
    events: list[str] = field(default_factory=_empty_str_list)


@dataclass
class Plugin:
    name: str
    version: str
    description: str
    author: str
    configuration: WaybillConfig = field(
        default_factory=lambda: WaybillConfig(
            kind="WaybillConfig",
            version="v1alpha1",
            metadata=ConfigMetadata(name="plugin-default"),
            spec=ConfigSpec(),
        )
    )
    fields: list[dict[str, Any]] = field(default_factory=_empty_any_list)
    actions: list[dict[str, Any]] = field(default_factory=_empty_any_list)

    def __post_init__(self):
        pass

    @staticmethod
    def _to_field(item: PluginField | Mapping[str, Any]) -> PluginField:
        if isinstance(item, PluginField):
            return item

        raw_type = item.get("type", PluginFieldType.STRING)
        field_type = (
            raw_type
            if isinstance(raw_type, PluginFieldType)
            else PluginFieldType(str(raw_type))
        )

        raw_options = item.get("options", [])
        options = (
            cast(list[Any], raw_options)
            if isinstance(raw_options, list)
            else _empty_any_list()
        )

        return PluginField(
            id=str(item.get("id", "")),
            label=str(item.get("label", "")),
            type=field_type,
            default=item.get("default"),
            description=str(item.get("description", "")),
            options=options,
        )

    @staticmethod
    def _to_action(item: PluginAction | Mapping[str, Any]) -> PluginAction:
        if isinstance(item, PluginAction):
            return item

        raw_confirm = item.get("confirm", {})
        confirm = (
            cast(dict[str, Any], raw_confirm)
            if isinstance(raw_confirm, dict)
            else _empty_str_any_dict()
        )

        raw_events = item.get("events", [])
        events = (
            [str(event) for event in cast(list[Any], raw_events)]
            if isinstance(raw_events, list)
            else _empty_str_list()
        )

        return PluginAction(
            id=str(item.get("id", "")),
            label=str(item.get("label", "")),
            description=str(item.get("description", "")),
            confirm=confirm,
            button_label=str(item.get("button_label", "")),
            button_variant=str(item.get("button_variant", "")),
            button_color=str(item.get("button_color", "")),
            events=events,
        )
