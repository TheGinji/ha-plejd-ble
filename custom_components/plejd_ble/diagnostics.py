"""Diagnostische gegevens voor Plejd BLE, zonder privégegevens."""

from __future__ import annotations

from typing import Any

from homeassistant.components import bluetooth
from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant

from .const import CONF_SITE_ID, CONF_SITE_TITLE
from .site import PlejdBleConfigEntry

TO_REDACT = {CONF_USERNAME, CONF_PASSWORD, CONF_SITE_ID, CONF_SITE_TITLE}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: PlejdBleConfigEntry
) -> dict[str, Any]:
    """Geef een samenvatting die alleen ongevoelige gegevens bevat.

    We nemen bewust niets over uit de cloudgegevens: namen, adressen en
    sleutels blijven buiten beeld. Per apparaat tonen we alleen technische
    kenmerken.
    """
    site = entry.runtime_data
    devices = []
    for device in site.devices:
        hardware = device.hw
        reading = site.signal.get(device.ble_mac.upper())
        devices.append(
            {
                "model": device.hardware,
                "firmware": str(device.firmware),
                "type": str(device.outputType),
                "capabilities": int(device.capabilities),
                "powered": device.powered,
                "is_primary": device.is_primary,
                "hidden": device.hidden,
                "is_gateway": hardware.is_gateway if hardware else None,
                "rssi_now": reading.rssi if reading else None,
                "last_seen": reading.seen_at.isoformat() if reading else None,
            }
        )
    return {
        "entry": {
            "version": entry.version,
            "data": async_redact_data(dict(entry.data), TO_REDACT),
        },
        "bluetooth": {
            "connectable_scanners": bluetooth.async_scanner_count(
                hass, connectable=True
            ),
            "mesh_connected": site.manager.connected,
        },
        "connection": {
            "ping_failures": site.ping_failures,
            "last_ping_failure": (
                site.last_ping_failure.isoformat() if site.last_ping_failure else None
            ),
            "recent_events": [
                {"at": moment.isoformat(), "connected": connected}
                for moment, connected in site.connection_events
            ],
        },
        "cache": {
            "last_fetched": (
                site.cache_fetched_at.isoformat() if site.cache_fetched_at else None
            ),
            "cloud_used_at_start": site.used_cloud,
        },
        "devices": devices,
    }
