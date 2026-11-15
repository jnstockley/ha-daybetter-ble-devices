"""Common device identity and connection availability."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import MANUFACTURER
from .coordinator import DaybetterLedStripCoordinator


class DaybetterLedStripEntity(CoordinatorEntity[DaybetterLedStripCoordinator]):
    """Superclass for all entities with device info and coordinator prefilled."""

    def __init__(self, coordinator: DaybetterLedStripCoordinator, key: str) -> None:
        """Initialize."""
        super().__init__(coordinator)
        self._attr_device_info = DeviceInfo(
            identifiers={
                (
                    coordinator.config_entry.domain,
                    coordinator.config_entry.entry_id,
                ),
            },
            manufacturer=MANUFACTURER,
            name=coordinator.config_entry.title,
        )
        self._attr_unique_id = (
            f"{self.coordinator.config_entry.runtime_data.device.address}_{key}"
        )

    @property
    def available(self) -> bool:
        """Require an established connection as well as a successful coordinator."""
        return bool(
            super().available
            and self.coordinator.data
            and self.coordinator.data["connected"]
        )
