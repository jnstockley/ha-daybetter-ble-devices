"""Entity state must reflect the coordinator immediately after setup."""

import logging
from types import SimpleNamespace

import pytest
from homeassistant.core import HomeAssistant

from custom_components.daybetter_led.coordinator import DaybetterLedStripCoordinator
from custom_components.daybetter_led.light import (
    ENTITY_DESCRIPTIONS,
    DaybetterLedStripLight,
)


@pytest.fixture
async def coordinator(tmp_path):
    hass = HomeAssistant(str(tmp_path))
    device = SimpleNamespace(
        address="AA:BB:CC:DD:EE:FF",
        connected=False,
        power=True,
        rssi=-60,
        color=(255, 0, 0),
        brightness=100,
        effect=None,
    )
    entry = SimpleNamespace(
        async_on_unload=lambda fn: None,
        domain="daybetter_led",
        entry_id="saved-entry",
        title="Saved strip",
        options={},
        pref_disable_polling=False,
        runtime_data=SimpleNamespace(device=device),
    )
    coordinator = DaybetterLedStripCoordinator(
        hass, logging.getLogger(__name__), name="daybetter_led", config_entry=entry
    )
    coordinator.refresh_state()
    return coordinator


async def test_disconnected_light_is_unavailable_on_creation(coordinator):
    light = DaybetterLedStripLight(coordinator, ENTITY_DESCRIPTIONS[0])
    assert not light.available
    assert light.unique_id == "AA:BB:CC:DD:EE:FF_lights"
    assert light.device_info["identifiers"] == {("daybetter_led", "saved-entry")}


async def test_connected_light_has_initial_state(coordinator):
    coordinator.config_entry.runtime_data.device.connected = True
    coordinator.refresh_state()
    light = DaybetterLedStripLight(coordinator, ENTITY_DESCRIPTIONS[0])
    assert light.available
    assert light.is_on is True
    assert light.rgb_color == (255, 0, 0)
    assert light.brightness == 255


async def test_rssi_updates_without_reconnecting_and_survives_state_notifications(
    coordinator,
):
    coordinator.async_update_rssi(-42)
    assert coordinator.data["rssi"] == -42
    coordinator.refresh_state()
    assert coordinator.data["rssi"] == -42
