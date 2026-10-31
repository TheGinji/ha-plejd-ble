"""Lampen en dimmers van Plejd."""

from __future__ import annotations

from typing import Any

from pyplejd import DeviceTypes

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_TEMP_KELVIN,
    ColorMode,
    LightEntity,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .entity import PlejdEntity
from .site import PlejdBleConfigEntry, PlejdSite

PARALLEL_UPDATES = 1


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PlejdBleConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Maak een lamp voor elke Plejd-uitgang van het type licht."""
    site = entry.runtime_data
    async_add_entities(
        PlejdLight(site, device)
        for device in site.devices_of_type(DeviceTypes.PlejdDeviceType.LIGHT)
    )


class PlejdLight(PlejdEntity, LightEntity):
    """Een Plejd-lamp of dimmer."""

    _attr_name = None

    def __init__(self, site: PlejdSite, device: Any) -> None:
        """Bepaal wat de lamp kan."""
        super().__init__(site, device)
        if device.colortemp:
            mode = ColorMode.COLOR_TEMP
            self._attr_min_color_temp_kelvin = device.colortemp[0]
            self._attr_max_color_temp_kelvin = device.colortemp[1]
        elif device.dimmable:
            mode = ColorMode.BRIGHTNESS
        else:
            mode = ColorMode.ONOFF
        self._attr_supported_color_modes = {mode}
        self._attr_color_mode = mode

    @property
    def is_on(self) -> bool | None:
        """Geef aan of de lamp aan staat (onbekend tot de eerste status binnen is)."""
        return self._data.get("state")

    @property
    def brightness(self) -> int | None:
        """Geef de helderheid van 0 tot 255."""
        dim = self._data.get("dim")
        if dim is None:
            return None
        return max(0, min(255, int(dim)))

    @property
    def color_temp_kelvin(self) -> int | None:
        """Geef de kleurtemperatuur in kelvin."""
        return self._data.get("colortemp")

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Zet de lamp aan, eventueel met helderheid of kleurtemperatuur."""
        self._raise_if_not_connected()
        kelvin = kwargs.get(ATTR_COLOR_TEMP_KELVIN)
        # pyplejd verwacht de kleurtemperatuur in mired en rekent zelf om.
        colortemp = 1e6 / kelvin if kelvin else None
        await self._device.turn_on(kwargs.get(ATTR_BRIGHTNESS), colortemp)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Zet de lamp uit."""
        self._raise_if_not_connected()
        await self._device.turn_off()
