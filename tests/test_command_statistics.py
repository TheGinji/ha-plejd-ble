"""Tests voor de opdrachtstatistieken in de diagnostische gegevens."""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import AsyncMock, patch

from pyplejd.interface.plejd_light import PlejdLight
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)

from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from custom_components.plejd_ble.diagnostics import async_get_config_entry_diagnostics

from . import DIMMER, get_device, get_entity, get_entity_id, push_state


async def light_command(
    hass: HomeAssistant, service: str, entity_id: str, **data: float
) -> None:
    """Stuur een opdracht naar een lamp, zonder dat het apparaat antwoordt."""
    with patch.object(PlejdLight, service, AsyncMock()):
        await hass.services.async_call(
            "light", service, {"entity_id": entity_id, **data}, blocking=True
        )


async def test_confirmed_command_is_counted_with_its_time(
    hass: HomeAssistant, loaded_entry: MockConfigEntry
) -> None:
    """Een bevestigde opdracht telt mee, met de tijd die het duurde."""
    entity_id = get_entity_id(hass, "light", DIMMER)
    device = get_device(loaded_entry, DIMMER)
    push_state(device, state=False, dim=0)
    await light_command(hass, "turn_on", entity_id, brightness=100)

    push_state(device, state=True, dim=100)

    commands = (await async_get_config_entry_diagnostics(hass, loaded_entry))["commands"]
    assert commands["sent"] == 1
    assert commands["confirmed"] == 1
    assert commands["unconfirmed"] == 0
    assert commands["confirm_seconds_avg"] >= 0
    assert commands["confirm_seconds_max"] >= 0


async def test_command_without_change_is_not_a_failure(
    hass: HomeAssistant, loaded_entry: MockConfigEntry
) -> None:
    """Een lamp die al uit staat meldt niets na uitzetten. Dat is geen mislukking."""
    entity_id = get_entity_id(hass, "light", DIMMER)
    push_state(get_device(loaded_entry, DIMMER), state=False, dim=0)
    await light_command(hass, "turn_off", entity_id)

    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=6))
    await hass.async_block_till_done()

    commands = (await async_get_config_entry_diagnostics(hass, loaded_entry))["commands"]
    assert commands["sent"] == 1
    assert commands["unchanged"] == 1
    assert commands["unconfirmed"] == 0
    assert commands["last_unconfirmed"] is None


async def test_replaced_command_is_counted_separately(
    hass: HomeAssistant, loaded_entry: MockConfigEntry
) -> None:
    """Komt er een nieuwe opdracht voor de bevestiging, dan telt de eerste als vervangen."""
    entity_id = get_entity_id(hass, "light", DIMMER)
    device = get_device(loaded_entry, DIMMER)
    push_state(device, state=False, dim=0)
    await light_command(hass, "turn_on", entity_id, brightness=50)
    await light_command(hass, "turn_on", entity_id, brightness=150)

    push_state(device, state=True, dim=150)

    commands = (await async_get_config_entry_diagnostics(hass, loaded_entry))["commands"]
    assert commands["sent"] == 2
    assert commands["superseded"] == 1
    assert commands["confirmed"] == 1
    assert commands["unconfirmed"] == 0


async def test_statistics_start_empty(
    hass: HomeAssistant, loaded_entry: MockConfigEntry
) -> None:
    """Zonder opdrachten is er niets om een gemiddelde van te nemen."""
    commands = (await async_get_config_entry_diagnostics(hass, loaded_entry))["commands"]
    assert commands == {
        "sent": 0,
        "confirmed": 0,
        "unconfirmed": 0,
        "unchanged": 0,
        "superseded": 0,
        "confirm_seconds_avg": None,
        "confirm_seconds_max": None,
        "late_confirmed": 0,
        "late_confirm_seconds_max": None,
        "last_unconfirmed": None,
    }


async def test_late_confirmation_is_counted(
    hass: HomeAssistant, loaded_entry: MockConfigEntry
) -> None:
    """Komt de bevestiging na de wachttijd, dan weten we dat de opdracht niet verloren ging."""
    entity_id = get_entity_id(hass, "light", DIMMER)
    device = get_device(loaded_entry, DIMMER)
    push_state(device, state=False, dim=0)
    await light_command(hass, "turn_on", entity_id, brightness=100)
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=6))
    await hass.async_block_till_done()

    push_state(device, state=True, dim=100)

    commands = (await async_get_config_entry_diagnostics(hass, loaded_entry))["commands"]
    assert commands["unconfirmed"] == 1
    assert commands["late_confirmed"] == 1
    assert commands["late_confirm_seconds_max"] >= 0


async def test_unrelated_report_after_the_wait_is_not_a_late_confirmation(
    hass: HomeAssistant, loaded_entry: MockConfigEntry
) -> None:
    """Een melding die niet is wat we vroegen, telt niet als te late bevestiging."""
    entity_id = get_entity_id(hass, "light", DIMMER)
    device = get_device(loaded_entry, DIMMER)
    push_state(device, state=False, dim=0)
    await light_command(hass, "turn_on", entity_id, brightness=100)
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=6))
    await hass.async_block_till_done()

    push_state(device, state=False, dim=0)

    commands = (await async_get_config_entry_diagnostics(hass, loaded_entry))["commands"]
    assert commands["unconfirmed"] == 1
    assert commands["late_confirmed"] == 0


async def test_report_long_after_the_command_is_not_counted_as_late(
    hass: HomeAssistant, loaded_entry: MockConfigEntry
) -> None:
    """Na het venster beschouwen we een passende melding als toeval."""
    entity_id = get_entity_id(hass, "light", DIMMER)
    device = get_device(loaded_entry, DIMMER)
    push_state(device, state=False, dim=0)
    await light_command(hass, "turn_on", entity_id, brightness=100)
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=6))
    await hass.async_block_till_done()
    get_entity(hass, entity_id)._assumed_at -= 31

    push_state(device, state=True, dim=100)

    commands = (await async_get_config_entry_diagnostics(hass, loaded_entry))["commands"]
    assert commands["unconfirmed"] == 1
    assert commands["late_confirmed"] == 0
