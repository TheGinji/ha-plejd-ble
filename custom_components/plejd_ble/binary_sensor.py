"""Bewegingssensoren van Plejd."""

from __future__ import annotations

from typing import Any

from pyplejd import DeviceTypes

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .entity import PlejdEntity
from .site import PlejdBleConfigEntry, PlejdSite

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PlejdBleConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Maak een bewegingssensor voor elk Plejd-apparaat dat beweging meldt."""
    site = entry.runtime_data
    async_add_entities(
        PlejdMotionSensor(site, device)
        for device in site.devices_of_type(DeviceTypes.PlejdDeviceType.MOTION)
    )


class PlejdMotionSensor(PlejdEntity, BinarySensorEntity):
    """Een Plejd-bewegingssensor."""

    _attr_device_class = BinarySensorDeviceClass.MOTION
    _attr_name = None

    def __init__(self, site: PlejdSite, device: Any) -> None:
        """Begin zonder beweging; de sensor meldt alleen als er iets gebeurt."""
        super().__init__(site, device)
        self._motion = False
        self._battery: int | None = None
        self._bright: bool | None = None

    @property
    def is_on(self) -> bool:
        """Geef aan of er beweging is."""
        return self._motion

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Geef batterij en lichtniveau mee zodra de sensor die doorgeeft."""
        attributes: dict[str, Any] = {}
        if self._battery is not None:
            attributes["battery"] = self._battery
        if self._bright is not None:
            attributes["bright"] = self._bright
        return attributes

    @callback
    def _handle_device_update(self, data: dict[str, Any]) -> None:
        """Verwerk een melding van de sensor."""
        if (motion := data.get("motion")) is not None:
            self._motion = bool(motion)
        if (battery := data.get("battery")) is not None:
            self._battery = battery
        if (bright := data.get("bright")) is not None:
            self._bright = bright
