"""Tests voor de velden waarmee apparaten in het apparaatregister komen."""

from __future__ import annotations

from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr

from custom_components.plejd_ble.const import DOMAIN

from . import RELAY_A, RELAY_B, get_device


async def test_registry_fields_are_plain_values(
    hass: HomeAssistant, loaded_entry: MockConfigEntry
) -> None:
    """De velden zijn een gewoon woordenboek, ook als DeviceInfo dat niet meer is.

    Vanaf Home Assistant 2026.11 is DeviceInfo geen woordenboek meer. Een
    woordenboek met velden werkt op elke versie.
    """
    site = loaded_entry.runtime_data
    primary_device = get_device(loaded_entry, RELAY_A)
    secondary_device = get_device(loaded_entry, RELAY_B)

    primary = site.device_registry_fields(primary_device)
    secondary = site.device_registry_fields(secondary_device)

    assert type(primary) is dict
    assert type(secondary) is dict
    assert primary["identifiers"] == {(DOMAIN, primary_device.device_identifier)}
    assert primary["connections"] == {
        (dr.CONNECTION_BLUETOOTH, primary_device.ble_mac)
    }
    assert "connections" not in secondary
    assert "via_device" not in primary
    assert "via_device" not in secondary
