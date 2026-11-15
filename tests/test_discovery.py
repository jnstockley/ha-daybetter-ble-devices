"""Discovery regressions using real HA flows and the published client's profiles."""

from types import SimpleNamespace

import pytest
from homeassistant.config_entries import ConfigEntries
from homeassistant.core import HomeAssistant

from custom_components.daybetter_led import config_flow


@pytest.fixture
async def flow(tmp_path):
    result = config_flow.DaybetterLedStripConfigFlow()
    result.hass = HomeAssistant(str(tmp_path))
    result.hass.config_entries = ConfigEntries(result.hass, {})
    result.context = {}
    return result


def advertisement(service, address="AA:BB:CC:DD:EE:FF", *, connectable=True):
    return SimpleNamespace(
        name="Daybetter test",
        address=address,
        service_uuids=[service],
        connectable=connectable,
    )


@pytest.mark.parametrize("model", ["031", "065"])
async def test_manual_discovery_supports_both_models(flow, monkeypatch, model):
    info = advertisement(f"0000c{model}-0000-1000-8000-00805f9b34fb")
    monkeypatch.setattr(
        config_flow, "async_discovered_service_info", lambda *a, **k: [info]
    )
    result = await flow.async_step_user()
    assert result["type"] == "form"
    assert result["data_schema"]({"address": info.address}) == {"address": info.address}


async def test_passive_and_unrelated_devices_are_excluded(flow, monkeypatch):
    infos = [
        advertisement("0000c031-0000-1000-8000-00805f9b34fb", connectable=False),
        advertisement("0000180f-0000-1000-8000-00805f9b34fb", "11:22:33:44:55:66"),
    ]
    monkeypatch.setattr(
        config_flow, "async_discovered_service_info", lambda *a, **k: infos
    )
    assert (await flow.async_step_user())["reason"] == "no_devices_found"


async def test_discovery_rejects_nonconnectable_device(flow):
    info = advertisement("0000c065-0000-1000-8000-00805f9b34fb", connectable=False)
    assert (await flow.async_step_bluetooth(info))["reason"] == "not_supported"


async def test_stale_selection_returns_form_error(flow):
    result = await flow.async_step_user({"address": "gone"})
    assert result["type"] == "form"
    assert result["errors"] == {"base": "device_unavailable"}
