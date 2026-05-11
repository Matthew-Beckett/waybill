from __future__ import annotations

import pytest

from src.types.config import WaybillConfig


def _valid_config_payload() -> dict[str, object]:
    return {
        "kind": "WaybillConfig",
        "version": "v1alpha1",
        "metadata": {"name": "demo"},
        "spec": {"profiles": {}},
    }


def test_waybill_config_accepts_supported_kind_and_version() -> None:
    cfg = WaybillConfig(**_valid_config_payload())
    assert cfg.kind == "WaybillConfig"
    assert cfg.version == "v1alpha1"


def test_waybill_config_rejects_unsupported_kind() -> None:
    payload = _valid_config_payload()
    payload["kind"] = "OtherConfig"

    with pytest.raises(ValueError, match="Unsupported config kind"):
        WaybillConfig(**payload)


def test_waybill_config_rejects_unsupported_version() -> None:
    payload = _valid_config_payload()
    payload["version"] = "v2"

    with pytest.raises(ValueError, match="Unsupported config version"):
        WaybillConfig(**payload)


def test_waybill_config_requires_non_empty_metadata_name() -> None:
    payload = _valid_config_payload()
    payload["metadata"] = {"name": "   "}

    with pytest.raises(ValueError, match="metadata.name must be a non-empty string"):
        WaybillConfig(**payload)
