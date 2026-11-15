"""
Custom integration to integrate daybetter_ble_client with Home Assistant.

For more details about this integration, please refer to
https://github.com/jnstockley/ha-daybetter-ble-devices
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from bleak.exc import BleakError
from daybetter_ble_client import DaybetterLedStrip
from homeassistant.components import bluetooth
from homeassistant.components.bluetooth.match import ADDRESS, BluetoothCallbackMatcher
from homeassistant.const import (
    CONF_ADDRESS,
    EVENT_HOMEASSISTANT_STOP,
    Platform,
)
from homeassistant.core import callback
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.loader import async_get_loaded_integration

from .connection import DaybetterConnection
from .const import DOMAIN
from .coordinator import DaybetterLedStripCoordinator
from .models import DaybetterLedStripData

if TYPE_CHECKING:
    from homeassistant.core import Event, HomeAssistant

    from .models import DaybetterLedStripConfigEntry


_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.LIGHT,
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: DaybetterLedStripConfigEntry,
) -> bool:
    """Set up this integration using UI."""
    address: str = entry.data[CONF_ADDRESS]

    led_strip = DaybetterLedStrip(address)
    connection = DaybetterConnection(led_strip)

    # It's fine if the device isn't available right now
    ble_device = bluetooth.async_last_service_info(
        hass, address.upper(), connectable=True
    )

    async def _async_reconnect(
        service_info: bluetooth.BluetoothServiceInfoBleak,
    ) -> None:
        try:
            await connection.async_update(service_info)
        except BleakError, TimeoutError:
            _LOGGER.warning(
                "Daybetter reconnect failed; waiting for another advertisement"
            )

    @callback
    def _async_update_ble(
        service_info: bluetooth.BluetoothServiceInfoBleak,
        _change: bluetooth.BluetoothChange,
    ) -> None:
        """Update from a ble callback."""
        coordinator.async_update_rssi(service_info.rssi)
        entry.async_create_background_task(
            hass, _async_reconnect(service_info), "Daybetter reconnect"
        )

    coordinator = DaybetterLedStripCoordinator(
        hass=hass, logger=_LOGGER, name=DOMAIN, config_entry=entry
    )
    entry.runtime_data = DaybetterLedStripData(
        device=led_strip,
        integration=async_get_loaded_integration(hass, entry.domain),
        coordinator=coordinator,
        connection=connection,
    )

    @callback
    def _on_strip_state_change() -> None:
        coordinator.refresh_state()

    # Listen for changes
    entry.async_on_unload(led_strip.on_change(_on_strip_state_change))

    # Seed availability before entities are created, even with no radio in range.
    coordinator.refresh_state()
    entry.async_on_unload(
        bluetooth.async_register_callback(
            hass,
            _async_update_ble,
            BluetoothCallbackMatcher({ADDRESS: address}),
            bluetooth.BluetoothScanningMode.PASSIVE,
        )
    )
    try:
        if ble_device is not None:
            await connection.async_update(ble_device)
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    except BaseException as err:
        await coordinator.async_shutdown()
        await connection.async_close()
        if isinstance(err, (BleakError, TimeoutError)):
            raise ConfigEntryNotReady(
                "Daybetter connection initialization failed"
            ) from err
        raise

    async def _async_stop(_event: Event) -> None:
        """Disconnect device after pending connection work stops."""
        await coordinator.async_shutdown()
        await connection.async_close()

    entry.async_on_unload(
        hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, _async_stop)
    )

    return True


async def async_unload_entry(
    hass: HomeAssistant,
    entry: DaybetterLedStripConfigEntry,
) -> bool:
    """Handle removal of an entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        await entry.runtime_data.connection.async_close()
    return unload_ok
