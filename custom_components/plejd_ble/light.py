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
from homeassistant.helpers.restore_state import RestoredExtraData, RestoreEntity

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


class PlejdLight(PlejdEntity, LightEntity, RestoreEntity):
    """Een Plejd-lamp of dimmer.

    Aan of uit en helderheid vraagt pyplejd bij elke verbinding op. De
    kleurtemperatuur meldt Plejd alleen als hij verandert, dus die zou na een
    herstart leeg zijn. Daarom bewaren we de laatst bekende kleurtemperatuur.
    """

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
        self._restored_kelvin: int | None = None

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
        """Geef de kleurtemperatuur in kelvin: de gemelde, anders de laatst bewaarde."""
        kelvin = self._data.get("colortemp")
        return kelvin if kelvin is not None else self._restored_kelvin

    @property
    def extra_restore_state_data(self) -> RestoredExtraData | None:
        """Bewaar de kleurtemperatuur, ook als de lamp uit staat."""
        if self._attr_color_mode is not ColorMode.COLOR_TEMP:
            return None
        return RestoredExtraData({"color_temp_kelvin": self.color_temp_kelvin})

    async def async_added_to_hass(self) -> None:
        """Herstel de laatste kleurtemperatuur en luister daarna naar de lamp."""
        if (
            self._attr_color_mode is ColorMode.COLOR_TEMP
            and (extra := await self.async_get_last_extra_data()) is not None
        ):
            kelvin = extra.as_dict().get("color_temp_kelvin")
            if isinstance(kelvin, int | float):
                self._restored_kelvin = int(kelvin)
        await super().async_added_to_hass()

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
