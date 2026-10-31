"""Plejd BLE: Plejd-verlichting in Home Assistant via Bluetooth."""

from __future__ import annotations

from homeassistant.const import EVENT_HOMEASSISTANT_STOP, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntry

from .const import DOMAIN
from .site import PlejdBleConfigEntry, PlejdSite, cache_store

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.EVENT,
    Platform.LIGHT,
    Platform.SWITCH,
]


async def async_setup_entry(hass: HomeAssistant, entry: PlejdBleConfigEntry) -> bool:
    """Zet een Plejd-site op."""
    site = PlejdSite(hass, entry)
    await site.async_load()
    entry.runtime_data = site

    site.async_register_devices()
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Bluetooth starten we pas als alle entiteiten er zijn, zodat ze de
    # eerste statusmeldingen niet missen.
    await site.async_start()
    entry.async_on_unload(
        hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, site.async_hass_stopping)
    )
    return True


async def async_unload_entry(hass: HomeAssistant, entry: PlejdBleConfigEntry) -> bool:
    """Haal een Plejd-site weer weg."""
    if not await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        return False
    await entry.runtime_data.async_stop()
    return True


async def async_remove_entry(hass: HomeAssistant, entry: PlejdBleConfigEntry) -> None:
    """Verwijder de lokaal bewaarde sitegegevens als het item wordt verwijderd."""
    await cache_store(hass, entry.entry_id).async_remove()


async def async_remove_config_entry_device(
    hass: HomeAssistant, entry: PlejdBleConfigEntry, device_entry: DeviceEntry
) -> bool:
    """Sta het verwijderen van een apparaat toe als het niet meer in de site zit."""
    active = {
        (DOMAIN, device.device_identifier)
        for device in entry.runtime_data.devices
        if device.outputType
    }
    return not active & device_entry.identifiers
