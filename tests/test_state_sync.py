"""Exercise HA state synchronization using the client and a simulated GATT radio."""

import asyncio
import logging
from types import SimpleNamespace

import pytest
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData
from bleak.exc import BleakError
from daybetter_ble_client import DaybetterLedStrip, led_strip
from daybetter_ble_client.const import P031, P065
from daybetter_ble_client.util import modbus
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.daybetter_led.connection import DaybetterConnection
from custom_components.daybetter_led.coordinator import DaybetterLedStripCoordinator
from custom_components.daybetter_led.light import (
    ENTITY_DESCRIPTIONS,
    DaybetterLedStripLight,
)


def packet(command, payload):
    body = bytes([0xA1, command, len(payload) + 3]) + payload
    return bytearray(body + modbus(body))


def snapshot(power=1, brightness=100):
    return packet(
        0x10, bytes([power, 1, 255, brightness, 50, 50, 17, 34, 51]) + bytes(5)
    )


class Radio:
    """Reply to handshake/status requests; never access physical Bluetooth."""

    def __init__(self):
        self.is_connected = True
        self.reply = snapshot()
        self.fail = False
        self.reads = 0
        self.callback = None

    async def start_notify(self, characteristic, callback):
        self.callback = callback

    async def write_gatt_char(self, characteristic, data, **kwargs):
        command = data[1]
        if self.fail:
            raise BleakError("Simulated radio failure")
        if command == 0:
            await self.callback(None, packet(0, b"CCHIP\x12\x34"))
        elif command == 1:
            await self.callback(None, packet(1, b"\x43\x00\x00\x00\x00\x01"))
        elif command == 0x10:
            self.reads += 1
            await self.callback(None, self.reply)

    async def stop_notify(self, characteristic):
        pass

    async def disconnect(self):
        self.is_connected = False


@pytest.fixture
async def setup_device(tmp_path, monkeypatch):
    owners = []
    coordinators = []

    async def setup(profile):
        radio = Radio()

        async def establish(*args, **kwargs):
            return radio

        monkeypatch.setattr(led_strip, "establish_connection", establish)
        device = DaybetterLedStrip("AA:BB:CC:DD:EE:FF")
        owner = DaybetterConnection(device)
        owners.append(owner)
        entry = SimpleNamespace(
            domain="daybetter_led",
            entry_id="existing",
            title="Strip",
            options={},
            state=ConfigEntryState.LOADED,
            pref_disable_polling=False,
            async_on_unload=lambda callback: None,
            runtime_data=SimpleNamespace(device=device, connection=owner),
        )
        hass = HomeAssistant(str(tmp_path))
        coordinator = DaybetterLedStripCoordinator(
            hass, logging.getLogger(__name__), name="daybetter_led", config_entry=entry
        )
        coordinators.append(coordinator)
        device.on_change(coordinator.refresh_state)
        coordinator.refresh_state()
        advertisement = AdvertisementData(
            profile.model, {}, {}, [profile.discovery_service], None, -60, ()
        )
        await owner.async_update(
            SimpleNamespace(
                device=BLEDevice(device.address, profile.model, {}),
                advertisement=advertisement,
            )
        )
        return coordinator, radio

    yield setup
    for coordinator in coordinators:
        await coordinator.async_shutdown()
    for owner in owners:
        await owner.async_close()


@pytest.mark.parametrize("profile", [P031, P065])
async def test_connect_populates_light_before_any_ha_command(setup_device, profile):
    coordinator, radio = await setup_device(profile)
    light = DaybetterLedStripLight(coordinator, ENTITY_DESCRIPTIONS[0])
    assert light.available
    assert not light.assumed_state
    assert light.is_on is True
    assert light.brightness == 255
    assert light.rgb_color == (17, 34, 51)
    assert radio.reads == 1


@pytest.mark.parametrize("profile", [P031, P065])
async def test_refresh_reconciles_external_change(setup_device, profile):
    coordinator, radio = await setup_device(profile)
    radio.reply = snapshot(power=0, brightness=25)
    await coordinator.async_refresh()
    assert coordinator.last_update_success
    assert coordinator.data["on"] is False
    assert coordinator.data["brightness"] == 25
    assert radio.reads == 2


async def test_remote_notification_immediately_updates_state(setup_device):
    coordinator, radio = await setup_device(P065)
    await radio.callback(None, snapshot(power=0, brightness=75))
    assert coordinator.data["on"] is False
    assert coordinator.data["brightness"] == 75
    assert radio.reads == 1


async def test_failed_poll_stays_failed_after_rssi_and_recovers_on_status(setup_device):
    coordinator, radio = await setup_device(P031)
    radio.fail = True
    await coordinator.async_refresh()
    assert not coordinator.last_update_success
    coordinator.async_update_rssi(-40)
    assert not coordinator.last_update_success
    assert coordinator.data["rssi"] == -40
    radio.fail = False
    radio.reply = snapshot(power=0)
    await coordinator.async_refresh()
    assert coordinator.last_update_success
    assert coordinator.data["on"] is False


async def test_client_disconnect_cause_is_logged_safely(setup_device, caplog):
    coordinator, radio = await setup_device(P031)
    device = coordinator.config_entry.runtime_data.device
    cause = OSError("remote closed AA:BB:CC:DD:EE:FF; packet a1 10 11 01 14 ff 64")
    started = asyncio.Event()

    async def stall_write(*_args, **_kwargs):
        started.set()
        await asyncio.Event().wait()

    radio.write_gatt_char = stall_write
    refresh = asyncio.create_task(coordinator._async_update_data())
    await started.wait()
    with caplog.at_level(logging.WARNING, logger=__name__), pytest.raises(UpdateFailed):
        device._on_disconnected(radio, cause)
        assert "OSError: remote closed <redacted address>" in caplog.text
        await refresh

    assert "OSError: remote closed <redacted address>" in caplog.text
    assert "<redacted data>" in caplog.text
    assert "AA:BB:CC:DD:EE:FF" not in caplog.text
    assert "a1 10 11 01 14 ff 64" not in caplog.text


async def test_rssi_does_not_postpone_periodic_poll(setup_device):
    coordinator, _ = await setup_device(P031)
    assert coordinator.update_interval.total_seconds() == 30
    unsubscribe = coordinator.async_add_listener(lambda: None)
    scheduled = coordinator._unsub_refresh
    coordinator.async_update_rssi(-50)
    assert coordinator._unsub_refresh is scheduled
    unsubscribe()


async def test_close_cancels_inflight_refresh_before_disconnect(setup_device):
    coordinator, radio = await setup_device(P065)
    owner = coordinator.config_entry.runtime_data.connection
    started = asyncio.Event()

    async def stall(*args, **kwargs):
        started.set()
        await asyncio.Event().wait()

    radio.write_gatt_char = stall
    task = asyncio.create_task(owner.async_refresh_state())
    await started.wait()
    await owner.async_close()
    assert task.cancelled()
    assert not radio.is_connected


async def test_remote_effect_updates_existing_light(setup_device, monkeypatch):
    coordinator, radio = await setup_device(P065)
    light = DaybetterLedStripLight(coordinator, ENTITY_DESCRIPTIONS[0])
    monkeypatch.setattr(light, "async_write_ha_state", lambda: None)
    unsubscribe = coordinator.async_add_listener(light._handle_coordinator_update)
    # Captured P065 status: FADE_RED_GREEN, power on, brightness 100.
    await radio.callback(
        None,
        bytearray.fromhex("a1 10 11 01 14 ff 64 32 32 ff 00 00 00 00 00 00 00 aa a3"),
    )
    assert light.effect == "fade_red_green"
    assert light.rgb_color is None
    assert light.is_on is True
    unsubscribe()
