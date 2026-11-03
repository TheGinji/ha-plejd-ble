"""Plejd-scènes: activeer een scène uit de Plejd-app met één bericht naar het mesh."""

from __future__ import annotations

from typing import Any

from pyplejd import DeviceTypes

from homeassistant.components.scene import Scene
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .site import PlejdBleConfigEntry, PlejdSite

PARALLEL_UPDATES = 1


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PlejdBleConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Maak een scène voor elke zichtbare scène uit de Plejd-app."""
    site = entry.runtime_data
    async_add_entities(PlejdSceneEntity(site, scene) for scene in site.scenes)


class PlejdSceneEntity(Scene):
    """Een scène uit de Plejd-app.

    Activeren is één bericht aan het mesh, in plaats van één bericht per lamp.
    Wat de scène precies doet, stel je in de Plejd-app in.
    """

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, site: PlejdSite, scene: DeviceTypes.PlejdScene) -> None:
        """Koppel de entiteit aan een scène uit pyplejd."""
        self._site = site
        self._scene = scene
        self._attr_name = scene.name
        self._attr_unique_id = f"{site.entry.entry_id}:scene:{scene.scene.sceneId}"

    @property
    def available(self) -> bool:
        """De scène is beschikbaar zolang het Bluetooth-mesh verbonden is."""
        return self._site.manager.connected

    async def async_added_to_hass(self) -> None:
        """Werk bij zodra de verbinding verandert."""
        await super().async_added_to_hass()
        self.async_on_remove(
            self._site.async_add_connection_listener(self.async_write_ha_state)
        )

    async def async_activate(self, **kwargs: Any) -> None:
        """Activeer de scène."""
        self._site.raise_if_not_connected()
        await self._scene.activate()
