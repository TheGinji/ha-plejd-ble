"""Tests voor de aangenomen stand: de tegel springt direct, het apparaat bevestigt daarna."""

from __future__ import annotations

from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from pyplejd.interface.plejd_light import PlejdLight
from pyplejd.interface.plejd_relay import PlejdRelay
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)

from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from custom_components.plejd_ble.diagnostics import async_get_config_entry_diagnostics

from . import DIMMER, RELAY_A, SPOT, get_device, get_entity_id, push_state


async def light_command(
    hass: HomeAssistant, service: str, entity_id: str, **data: float
) -> AsyncMock:
    """Stuur een opdracht naar een lamp, zonder dat het apparaat antwoordt."""
    with patch.object(PlejdLight, service, AsyncMock()) as command:
        await hass.services.async_call(
            "light", service, {"entity_id": entity_id, **data}, blocking=True
        )
    return command


async def test_light_shows_the_request_before_the_device_confirms(
    hass: HomeAssistant, loaded_entry: MockConfigEntry
) -> None:
    """Na aanzetten staat de lamp direct aan, met de gevraagde helderheid."""
    entity_id = get_entity_id(hass, "light", DIMMER)
    push_state(get_device(loaded_entry, DIMMER), state=False, dim=0)
    assert hass.states.get(entity_id).state == "off"

    await light_command(hass, "turn_on", entity_id, brightness=100)

    state = hass.states.get(entity_id)
    assert state.state == "on"
    assert state.attributes["brightness"] == 100


async def test_confirmation_hands_over_to_the_real_state(
    hass: HomeAssistant, loaded_entry: MockConfigEntry
) -> None:
    """Meldt het apparaat wat we vroegen, dan telt weer alleen wat het apparaat meldt."""
    entity_id = get_entity_id(hass, "light", DIMMER)
    device = get_device(loaded_entry, DIMMER)
    push_state(device, state=False, dim=0)
    await light_command(hass, "turn_on", entity_id, brightness=100)

    push_state(device, state=True, dim=101)
    assert hass.states.get(entity_id).attributes["brightness"] == 101

    push_state(device, state=True, dim=40)
    assert hass.states.get(entity_id).attributes["brightness"] == 40


async def test_report_without_the_asked_value_does_not_confirm(
    hass: HomeAssistant, loaded_entry: MockConfigEntry
) -> None:
    """Een melding die de gevraagde waarde niet noemt of niet haalt, bevestigt niets."""
    entity_id = get_entity_id(hass, "light", DIMMER)
    device = get_device(loaded_entry, DIMMER)
    push_state(device, state=False, dim=0)
    await light_command(hass, "turn_on", entity_id, brightness=100)

    push_state(device, state=True, dim=None)
    assert hass.states.get(entity_id).attributes["brightness"] == 100

    push_state(device, state=True, dim=20)
    assert hass.states.get(entity_id).attributes["brightness"] == 100

    push_state(device, state=True, dim=100)
    assert hass.states.get(entity_id).attributes["brightness"] == 100


async def test_without_confirmation_the_tile_falls_back(
    hass: HomeAssistant, loaded_entry: MockConfigEntry
) -> None:
    """Komt er binnen enkele seconden geen bevestiging, dan geldt weer de gemelde stand."""
    entity_id = get_entity_id(hass, "light", DIMMER)
    push_state(get_device(loaded_entry, DIMMER), state=False, dim=0)
    await light_command(hass, "turn_on", entity_id)
    assert hass.states.get(entity_id).state == "on"

    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=6))
    await hass.async_block_till_done()

    assert hass.states.get(entity_id).state == "off"
    result = await async_get_config_entry_diagnostics(hass, loaded_entry)
    assert result["commands"]["unconfirmed"] == 1
    assert result["commands"]["last_unconfirmed"] is not None


async def test_lost_connection_is_not_an_unconfirmed_command(
    hass: HomeAssistant,
    loaded_entry: MockConfigEntry,
    mocks: SimpleNamespace,
) -> None:
    """Valt de verbinding weg, dan tellen we de uitblijvende bevestiging niet mee."""
    entity_id = get_entity_id(hass, "light", DIMMER)
    push_state(get_device(loaded_entry, DIMMER), state=False, dim=0)
    await light_command(hass, "turn_on", entity_id)

    mocks.mesh.connected.return_value = False
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=6))
    await hass.async_block_till_done()

    assert loaded_entry.runtime_data.unconfirmed_commands == 0


async def test_turn_off_is_shown_right_away(
    hass: HomeAssistant, loaded_entry: MockConfigEntry
) -> None:
    """Na uitzetten staat de lamp direct uit."""
    entity_id = get_entity_id(hass, "light", DIMMER)
    push_state(get_device(loaded_entry, DIMMER), state=True, dim=200)
    assert hass.states.get(entity_id).state == "on"

    await light_command(hass, "turn_off", entity_id)

    assert hass.states.get(entity_id).state == "off"


async def test_color_temperature_is_never_assumed(
    hass: HomeAssistant, loaded_entry: MockConfigEntry
) -> None:
    """Aan of uit nemen we aan, de kleurtemperatuur tonen we alleen als gemeld."""
    entity_id = get_entity_id(hass, "light", SPOT)
    push_state(get_device(loaded_entry, SPOT), state=False, dim=0, colortemp=2700)

    command = await light_command(hass, "turn_on", entity_id, color_temp_kelvin=3500)

    state = hass.states.get(entity_id)
    assert state.state == "on"
    assert state.attributes["color_temp_kelvin"] == 2700
    brightness, colortemp = command.await_args.args
    assert brightness is None
    assert round(colortemp) == round(1e6 / 3500)


async def test_switch_shows_the_request_before_the_device_confirms(
    hass: HomeAssistant, loaded_entry: MockConfigEntry
) -> None:
    """Een relais springt na een opdracht ook direct."""
    entity_id = get_entity_id(hass, "switch", RELAY_A)
    push_state(get_device(loaded_entry, RELAY_A), state=False)
    assert hass.states.get(entity_id).state == "off"

    with patch.object(PlejdRelay, "turn_on", AsyncMock()):
        await hass.services.async_call(
            "switch", "turn_on", {"entity_id": entity_id}, blocking=True
        )
    assert hass.states.get(entity_id).state == "on"

    with patch.object(PlejdRelay, "turn_off", AsyncMock()):
        await hass.services.async_call(
            "switch", "turn_off", {"entity_id": entity_id}, blocking=True
        )
    assert hass.states.get(entity_id).state == "off"
