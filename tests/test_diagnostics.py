"""Tests voor de diagnostische gegevens van Plejd BLE."""

from __future__ import annotations

import json

from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.core import HomeAssistant

from custom_components.plejd_ble.diagnostics import async_get_config_entry_diagnostics


async def test_diagnostics_hide_private_data(
    hass: HomeAssistant, loaded_entry: MockConfigEntry
) -> None:
    """De diagnostische gegevens bevatten geen namen, adressen of sleutels."""
    result = await async_get_config_entry_diagnostics(hass, loaded_entry)
    text = json.dumps(result)

    for private in (
        "gebruiker@example.com",
        "geheim-wachtwoord",
        "site-1",
        "Voorbeeldstraat",
        "A0B1C2000001",
        "00112233445566778899AABBCCDDEEFF",
        "Zithoek",
    ):
        assert private not in text
    assert result["entry"]["data"]["password"] == "**REDACTED**"


async def test_diagnostics_describe_the_setup(
    hass: HomeAssistant, loaded_entry: MockConfigEntry
) -> None:
    """Wel zichtbaar: modellen, firmware en of de verbinding er is."""
    result = await async_get_config_entry_diagnostics(hass, loaded_entry)

    assert result["bluetooth"] == {"connectable_scanners": 1, "mesh_connected": True}
    assert result["cache"]["cloud_used_at_start"] is False
    assert result["cache"]["last_fetched"] is not None
    assert len(result["devices"]) == 11
    assert {device["model"] for device in result["devices"]} == {
        "DIM-02-LC2",
        "CCL-01",
        "DWN-02",
        "REL-01-2P",
        "WPH-01-LC",
        "WMS-01",
    }
    assert {device["firmware"] for device in result["devices"]} == {"1.2.3"}
