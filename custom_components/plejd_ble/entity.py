"""Basisklasse voor alle Plejd BLE-entiteiten."""

from __future__ import annotations

from typing import Any

from homeassistant.core import callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity import Entity

from .const import DOMAIN
from .site import PlejdSite


class PlejdEntity(Entity):
    """Een entiteit die bij één Plejd-apparaat hoort."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, site: PlejdSite, device: Any) -> None:
        """Koppel de entiteit aan een apparaat uit pyplejd."""
        self._site = site
        self._device = device
        self._data: dict[str, Any] = {}
        self._attr_unique_id = ":".join(device.identifier)
        self._attr_device_info = site.entity_device_info(device)
        self._attr_entity_registry_visible_default = not device.hidden

    @property
    def available(self) -> bool:
        """De entiteit is beschikbaar zolang het Bluetooth-mesh verbonden is."""
        return self._site.manager.connected

    async def async_added_to_hass(self) -> None:
        """Luister naar wijzigingen van het apparaat."""
        self.async_on_remove(self._device.subscribe(self._async_device_updated))

    @callback
    def _async_device_updated(self, data: dict[str, Any]) -> None:
        """Verwerk een nieuwe status van het apparaat."""
        self._data = data
        self._handle_device_update(data)
        self.async_write_ha_state()

    @callback
    def _handle_device_update(self, data: dict[str, Any]) -> None:
        """Laat subklassen op een wijziging reageren."""

    def _raise_if_not_connected(self) -> None:
        """Geef een duidelijke fout als er geen Bluetooth-verbinding is.

        pyplejd negeert opdrachten zonder verbinding stilletjes, dus dat
        controleren we zelf.
        """
        if not self._site.manager.connected:
            raise HomeAssistantError(
                translation_domain=DOMAIN, translation_key="not_connected"
            )
