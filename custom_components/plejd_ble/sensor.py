"""Diagnostische sensor: wanneer is de apparatenlijst voor het laatst opgehaald?"""

from __future__ import annotations

from datetime import datetime

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .site import PlejdBleConfigEntry, PlejdSite

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PlejdBleConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Maak de sensor voor het laatste ophalen uit de cloud."""
    async_add_entities([PlejdLastCloudSync(entry.runtime_data)])


class PlejdLastCloudSync(SensorEntity):
    """Het tijdstip waarop de apparatenlijst voor het laatst uit de cloud kwam."""

    _attr_has_entity_name = True
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False
    _attr_translation_key = "last_cloud_sync"

    def __init__(self, site: PlejdSite) -> None:
        """Koppel de sensor aan de site."""
        self._site = site
        self._attr_unique_id = f"{site.entry.entry_id}:last_cloud_sync"
        self._attr_device_info = site.hub_device_info()

    @property
    def native_value(self) -> datetime | None:
        """Geef het tijdstip, of niets als er nog niets is opgehaald."""
        return self._site.cache_fetched_at
