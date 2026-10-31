"""Tests voor Plejd BLE."""

from __future__ import annotations

from typing import Any

from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.helpers.entity_platform import async_get_platforms

from custom_components.plejd_ble.const import DOMAIN

# Unieke ID's van de entiteiten in tests/fixtures/site_details.json.
DIMMER = "A0B1C2000001:O:0"  # Zithoek
CEILING_1 = "A0B1C2000002:O:0"  # Slaapkamer 1 Plafondlicht
CEILING_2 = "A0B1C2000003:O:0"  # Slaapkamer 2 Plafondlicht
SPOT = "A0B1C2000004:O:0"  # Spot, met kleurtemperatuur
RELAY_A = "A0B1C2000005:O:0"  # Wandlamp
RELAY_B = "A0B1C2000005:O:1"  # Tuinlamp
BUTTON_DEVICE = "A0B1C2000006:I:0"  # Knop 1 van het paneel
BUTTON_ENTITY = f"{BUTTON_DEVICE}:press"
MOTION = "A0B1C2000007:I:0"  # Bewegingssensor
NUMBER_OF_ENTITIES = 11


async def setup_integration(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    """Zet de integratie op en wacht tot alles klaar is."""
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


def get_entity_id(hass: HomeAssistant, domain: str, unique_id: str) -> str:
    """Zoek het entiteit-ID bij een unieke ID."""
    entity_id = er.async_get(hass).async_get_entity_id(domain, DOMAIN, unique_id)
    assert entity_id is not None, f"Geen entiteit gevonden voor {unique_id}"
    return entity_id


def get_device_entry(
    hass: HomeAssistant, entry: MockConfigEntry, identifier: str
) -> dr.DeviceEntry | None:
    """Zoek een apparaat in het register, zonder verouderde functies te gebruiken."""
    for device in dr.async_entries_for_config_entry(dr.async_get(hass), entry.entry_id):
        if (DOMAIN, identifier) in device.identifiers:
            return device
    return None


def get_entity(hass: HomeAssistant, entity_id: str) -> Any:
    """Geef het entiteitsobject, zodat we het direct kunnen aanroepen."""
    for platform in async_get_platforms(hass, DOMAIN):
        if entity_id in platform.entities:
            return platform.entities[entity_id]
    raise AssertionError(f"Geen entiteitsobject voor {entity_id}")


def get_device(entry: MockConfigEntry, identifier: str) -> Any:
    """Geef het pyplejd-apparaat met deze identifier."""
    return next(
        device
        for device in entry.runtime_data.devices
        if ":".join(device.identifier) == identifier
    )


def push_state(device: Any, **state: Any) -> None:
    """Doe alsof het apparaat een nieuwe status meldt."""
    device._state.update(state)
    push_update(device, device._state)


def push_update(device: Any, data: dict[str, Any]) -> None:
    """Stuur een melding naar alle luisteraars van het apparaat."""
    for listener in list(device._listeners):
        listener(data)
