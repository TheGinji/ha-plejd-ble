"""Plejd BLE: Plejd-verlichting in Home Assistant via Bluetooth."""

from __future__ import annotations

from homeassistant.const import EVENT_HOMEASSISTANT_STOP, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.device_registry import DeviceEntry

from .const import DOMAIN
from .site import PlejdBleConfigEntry, PlejdSite, cache_store

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.EVENT,
    Platform.LIGHT,
    Platform.SENSOR,
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
    entry.async_on_unload(entry.add_update_listener(_async_options_updated))
    entry.async_on_unload(
        hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, site.async_hass_stopping)
    )
    return True


async def _async_options_updated(hass: HomeAssistant, entry: PlejdBleConfigEntry) -> None:
    """Pas gewijzigde opties direct toe."""
    await entry.runtime_data.async_apply_options()


async def async_unload_entry(hass: HomeAssistant, entry: PlejdBleConfigEntry) -> bool:
    """Haal een Plejd-site weer weg."""
    if not await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        return False
    await entry.runtime_data.async_stop()
    return True


async def async_remove_entry(hass: HomeAssistant, entry: PlejdBleConfigEntry) -> None:
    """Ruim lokaal bewaarde sitegegevens en meldingen op bij verwijderen."""
    await cache_store(hass, entry.entry_id).async_remove()
    ir.async_delete_issue(hass, DOMAIN, f"cloud_unreachable_{entry.entry_id}")


async def async_remove_config_entry_device(
    hass: HomeAssistant, entry: PlejdBleConfigEntry, device_entry: DeviceEntry
) -> bool:
    """Sta het verwijderen van een apparaat toe als het niet meer in de site zit."""
    active = {
        (DOMAIN, device.device_identifier)
        for device in entry.runtime_data.devices
        if device.outputType
    }
    active.add((DOMAIN, entry.entry_id))
    return not active & device_entry.identifiers
