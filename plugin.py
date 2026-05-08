import os
import sys

# Dirty hack to bring our own vendored dependencies without interfering with the host's Python environment
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src", "vendor"))

import json
import yaml
from dacite import Config, from_dict
from typing import Any

from .src.types.plugins import Plugin as DispatcharrPlugin
from .src.types.plugins import PluginFieldType
from .src.types.config import WaybillConfig
from .src.pipeline import WaybillPipeline, WaybillPlanFormatter
from .src.apply import WaybillApplier

class Plugin(DispatcharrPlugin):
    def __init__(self, path: str = "plugin.json") -> None:
        # This is a hack and could possibly be fragile in the even the way the plugin is loaded changes, 
        # But it allows us to keep the plugin manifest as the source of truth instead of the cursed bump_version.py
        # in Stream-Mappar.
        plugin_dir = os.path.dirname(os.path.abspath(__file__))
        plugin = self._load_manifest(os.path.join(plugin_dir, path))
        super().__init__(
            name=plugin.name,
            version=plugin.version,
            description=plugin.description,
            author=plugin.author,
            fields=plugin.fields,
            actions=plugin.actions
        )

        return None

    def _load_manifest(self, path: str) -> DispatcharrPlugin:
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)

        return from_dict(
            data_class=DispatcharrPlugin,
            data=raw,
            config=Config(cast=[PluginFieldType]),
        )

    def _load_configuration(self, context: dict[str, Any]) -> None:
        # Something, something exception handlers in Python are expensive...
        # Don't @ me about this, it's just easier to read than a million nested if statements and try/except blocks
        config_data = context.get("settings", {})
        manifest_str = config_data.get("manifest", "")
        if not manifest_str:
            raise Exception("Configuration manifest is empty or missing")
        try:
            parsed = yaml.safe_load(manifest_str)
        except yaml.YAMLError as e:
            raise Exception(f"Configuration manifest is not valid YAML: {e}")
        if not isinstance(parsed, dict):
            raise Exception(f"Configuration manifest did not parse to a mapping (got {type(parsed).__name__})")
        try:
            self.configuration = WaybillConfig(**{str(k): v for k, v in parsed.items()})  # type: ignore[call-arg]
        except Exception as e:
            raise Exception(f"Configuration is not valid: {e}") from e

        return None

    def _run_plan(self, logger: Any) -> None:
        pipeline = WaybillPipeline(self.configuration)
        plan = pipeline.compute_plan()
        formatter = WaybillPlanFormatter()
        for line in formatter.format(plan):
            logger.info(line)

    def _run_apply(self, logger: Any, params: dict[str, Any], context: dict[str, Any]) -> None:
        mode = (
            params.get("mode")
            or context.get("settings", {}).get("apply_mode")
            or "upsert"
        )
        pipeline = WaybillPipeline(self.configuration)
        plan = pipeline.compute_plan()
        applier = WaybillApplier(plan, mode, logger)
        applier.apply()

    def run(self, action: str, params: dict[str, Any], context: dict[str, dict[str, Any]]) -> None:
        self._load_configuration(context)
        logger = context.get("logger")

        if action == "plan":
            self._run_plan(logger)
            return None

        if action == "apply":
            self._run_apply(logger, params, context)
            return None

        logger.warning(f"Unknown action: {action!r}")
        return None
