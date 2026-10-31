"""Knoppen van Plejd, als events voor automatiseringen."""

from __future__ import annotations

from typing import Any

from pyplejd import DeviceTypes

from homeassistant.components.event import EventDeviceClass, EventEntity
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
    """Maak een event voor elke knop."""
    site = entry.runtime_data
    async_add_entities(
        PlejdButtonEvent(site, device)
        for device in site.devices_of_type(DeviceTypes.PlejdDeviceType.BUTTON)
    )


class PlejdButtonEvent(PlejdEntity, EventEntity):
    """Een knop op een Plejd-paneel."""

    _attr_device_class = EventDeviceClass.BUTTON
    _attr_event_types = ["press", "release"]
    _attr_translation_key = "button"

    def __init__(self, site: PlejdSite, device: Any) -> None:
        """Geef de knop een nummer, te beginnen bij 1."""
        super().__init__(site, device)
        self._attr_unique_id = f"{self._attr_unique_id}:press"
        self._attr_translation_placeholders = {"number": str(device.button_id + 1)}

    @callback
    def _handle_device_update(self, data: dict[str, Any]) -> None:
        """Geef een druk op de knop door."""
        action = data.get("action")
        if action in self._attr_event_types:
            self._trigger_event(action)
