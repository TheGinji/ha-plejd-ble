"""Relais en schakelaars van Plejd."""

from __future__ import annotations

from typing import Any

from pyplejd import DeviceTypes

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .entity import PlejdEntity
from .site import PlejdBleConfigEntry

PARALLEL_UPDATES = 1


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PlejdBleConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Maak een schakelaar voor elke Plejd-uitgang van het type relais."""
    site = entry.runtime_data
    async_add_entities(
        PlejdSwitch(site, device)
        for device in site.devices_of_type(DeviceTypes.PlejdDeviceType.SWITCH)
    )


class PlejdSwitch(PlejdEntity, SwitchEntity):
    """Een Plejd-relais."""

    _attr_name = None

    @property
    def is_on(self) -> bool | None:
        """Geef aan of het relais aan staat."""
        return self._data.get("state")

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Zet het relais aan."""
        self._raise_if_not_connected()
        await self._device.turn_on()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Zet het relais uit."""
        self._raise_if_not_connected()
        await self._device.turn_off()
