"""Bewegingssensoren van Plejd en de status van de Bluetooth-verbinding."""

from __future__ import annotations

from typing import Any

from pyplejd import DeviceTypes

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.const import EntityCategory
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
    """Maak de verbindingssensor en een bewegingssensor per Plejd-sensor."""
    site = entry.runtime_data
    entities: list[BinarySensorEntity] = [PlejdMeshConnected(site)]
    entities.extend(
        PlejdMotionSensor(site, device)
        for device in site.devices_of_type(DeviceTypes.PlejdDeviceType.MOTION)
    )
    async_add_entities(entities)


class PlejdMeshConnected(BinarySensorEntity):
    """Meldt of Home Assistant verbonden is met het Plejd-mesh."""

    _attr_has_entity_name = True
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_should_poll = False
    _attr_translation_key = "mesh_connected"

    def __init__(self, site: PlejdSite) -> None:
        """Koppel de sensor aan de site."""
        self._site = site
        self._attr_unique_id = f"{site.entry.entry_id}:mesh_connected"
        self._attr_device_info = site.hub_device_info()

    @property
    def is_on(self) -> bool:
        """Geef aan of er een Bluetooth-verbinding met het mesh is."""
        return self._site.manager.connected

    @property
    def extra_state_attributes(self) -> dict[str, str]:
        """Geef de naam van het apparaat waarlangs we verbonden zijn."""
        if via := self._site.connected_via():
            return {"connected_via": via}
        return {}

    async def async_added_to_hass(self) -> None:
        """Werk bij zodra de verbinding verandert."""
        self.async_on_remove(
            self._site.async_add_connection_listener(self.async_write_ha_state)
        )


class PlejdMotionSensor(PlejdEntity, BinarySensorEntity):
    """Een Plejd-bewegingssensor."""

    _attr_device_class = BinarySensorDeviceClass.MOTION
    _attr_name = None

    def __init__(self, site: PlejdSite, device: Any) -> None:
        """Begin zonder beweging; de sensor meldt alleen als er iets gebeurt."""
        super().__init__(site, device)
        self._motion = False
        self._bright: bool | None = None

    @property
    def is_on(self) -> bool:
        """Geef aan of er beweging is."""
        return self._motion

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Geef het lichtniveau mee zodra de sensor dat doorgeeft."""
        if self._bright is None:
            return {}
        return {"bright": self._bright}

    @callback
    def _handle_device_update(self, data: dict[str, Any]) -> None:
        """Verwerk een melding van de sensor."""
        if (motion := data.get("motion")) is not None:
            self._motion = bool(motion)
        if (bright := data.get("bright")) is not None:
            self._bright = bright
