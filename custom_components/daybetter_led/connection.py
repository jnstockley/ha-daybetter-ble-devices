"""Own advertisement-driven connection work for one configuration entry."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from bleak.exc import BleakError

if TYPE_CHECKING:
    from daybetter_ble_client import DaybetterLedStrip
    from homeassistant.components.bluetooth import BluetoothServiceInfoBleak


class DaybetterConnection:
    """Coalesce reconnection attempts and stop them before disconnecting."""

    def __init__(self, device: DaybetterLedStrip) -> None:
        """Initialize an entry-scoped connection owner."""
        self.device = device
        self._task: asyncio.Task | None = None
        self._closed = False
        self._refresh_tasks: set[asyncio.Task] = set()

    async def async_update(self, info: BluetoothServiceInfoBleak) -> None:
        """Connect using HA's latest device without disrupting a live session."""
        if self._closed or self.device.connected or self._task is not None:
            return
        self._task = asyncio.current_task()
        try:
            await self.device.update_device(info.device, info.advertisement)
        finally:
            self._task = None

    async def async_refresh_state(self) -> None:
        """Track status reads so unload can cancel them before disconnecting."""
        if self._closed:
            raise BleakError("Daybetter connection is closed")
        task = asyncio.current_task()
        self._refresh_tasks.add(task)
        try:
            await self.device.async_refresh_state()
        finally:
            self._refresh_tasks.discard(task)

    async def async_close(self) -> None:
        """Cancel and await pending setup before releasing the BLE connection."""
        self._closed = True
        tasks = set(self._refresh_tasks)
        if self._task is not None:
            tasks.add(self._task)
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        await self.device.disconnect()
