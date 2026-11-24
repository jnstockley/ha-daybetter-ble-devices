"""DataUpdateCoordinator for daybetter_ble_client."""

from __future__ import annotations

import logging
from dataclasses import asdict
from datetime import timedelta
from typing import TYPE_CHECKING

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .diagnostics import exception_summary
from .models import DaybetterLedStripState

if TYPE_CHECKING:
    from .models import DaybetterLedStripConfigEntry


class DaybetterLedStripCoordinator(DataUpdateCoordinator):
    """Class to manage pushing data from device."""

    config_entry: DaybetterLedStripConfigEntry
    _latest_rssi: int | None = None
    _last_state_update: float | None = None

    def __init__(
        self,
        hass: HomeAssistant,
        logger: logging.Logger,
        *,
        name: str,
        config_entry: DaybetterLedStripConfigEntry,
    ) -> None:
        """Poll current state while preserving immediate notification updates."""
        super().__init__(
            hass,
            logger,
            name=name,
            config_entry=config_entry,
            update_interval=timedelta(seconds=30),
            always_update=False,
        )
        self._last_logged_failure: str | None = None

    async def _async_update_data(self) -> dict:
        """Read device state instead of reporting cached values as a fresh poll."""
        try:
            await self.config_entry.runtime_data.connection.async_refresh_state()
        except Exception as err:
            device = self.config_entry.runtime_data.device
            disconnect_reason = getattr(device, "disconnect_reason", None)
            detail = (
                disconnect_reason if isinstance(disconnect_reason, Exception) else err
            )
            self._log_transport_failure("Daybetter status read failed", detail)
            raise UpdateFailed("Daybetter status read failed") from err
        self._last_logged_failure = None
        return self._snapshot()

    @callback
    def async_update_rssi(self, rssi: int) -> None:
        """Refresh signal strength without reopening the active connection."""
        self._latest_rssi = rssi
        self.refresh_state()

    @callback
    def refresh_state(self) -> None:
        """Refresh the state from the device and push to entities."""
        disconnect_reason = getattr(
            self.config_entry.runtime_data.device, "disconnect_reason", None
        )
        if isinstance(disconnect_reason, Exception):
            self._log_transport_failure(
                "Daybetter BLE connection disconnected", disconnect_reason
            )
        snapshot = self._snapshot()
        observed = getattr(
            self.config_entry.runtime_data.device, "last_state_update", None
        )
        if observed is not None and observed != self._last_state_update:
            self._last_state_update = observed
            self.async_set_updated_data(snapshot)
        else:
            # RSSI, disconnects and command acknowledgements are not fresh reads.
            # Do not hide a failed read or move its next scheduled attempt.
            self.data = snapshot
            self.async_update_listeners()

    def _log_transport_failure(self, event: str, error: BaseException) -> None:
        """Log a distinct BLE failure once, with private radio data redacted."""
        summary = exception_summary(error)
        if summary != self._last_logged_failure:
            self.logger.warning("%s: %s", event, summary)
        self._last_logged_failure = summary

    def _snapshot(self) -> dict:
        """Copy the client snapshot and latest advertisement signal strength."""
        state = DaybetterLedStripState(
            connected=self.config_entry.runtime_data.device.connected,
            on=self.config_entry.runtime_data.device.power,
            rssi=self._latest_rssi
            if self._latest_rssi is not None
            else self.config_entry.runtime_data.device.rssi,
            color=self.config_entry.runtime_data.device.color,
            brightness=self.config_entry.runtime_data.device.brightness,
            effect=self.config_entry.runtime_data.device.effect,
        )
        return asdict(state)
