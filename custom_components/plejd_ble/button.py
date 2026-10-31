"""Knop om de apparatenlijst opnieuw uit de Plejd-cloud te halen."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .site import PlejdBleConfigEntry, PlejdSite

PARALLEL_UPDATES = 1


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PlejdBleConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Maak de verversknop voor deze site."""
    async_add_entities([PlejdRefreshButton(entry.runtime_data)])


class PlejdRefreshButton(ButtonEntity):
    """Haalt de apparatenlijst bij de volgende keer opnieuw uit de cloud."""

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.CONFIG
    _attr_translation_key = "refresh_cloud"

    def __init__(self, site: PlejdSite) -> None:
        """Koppel de knop aan de site."""
        self._site = site
        self._attr_unique_id = f"{site.entry.entry_id}:refresh_cloud"
        self._attr_device_info = site.hub_device_info()

    async def async_press(self) -> None:
        """Vraag een verse apparatenlijst en laad de integratie opnieuw."""
        self._site.async_request_refresh()
