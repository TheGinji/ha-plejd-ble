"""Tests voor de entiteiten van Plejd BLE."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from pyplejd.interface.plejd_light import PlejdLight
from pyplejd.interface.plejd_relay import PlejdRelay
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from . import (
    BUTTON_DEVICE,
    BUTTON_ENTITY,
    DIMMER,
    MOTION,
    RELAY_A,
    SPOT,
    get_device,
    get_entity,
    get_entity_id,
    push_state,
    push_update,
)


async def test_light_is_unknown_until_status_arrives(
    hass: HomeAssistant, loaded_entry: MockConfigEntry
) -> None:
    """Zolang de lamp niets heeft gemeld, is de status onbekend."""
    state = hass.states.get(get_entity_id(hass, "light", DIMMER))

    assert state is not None
    assert state.state == "unknown"


async def test_light_follows_reported_state(
    hass: HomeAssistant, loaded_entry: MockConfigEntry
) -> None:
    """De lamp volgt wat het apparaat meldt."""
    entity_id = get_entity_id(hass, "light", DIMMER)
    device = get_device(loaded_entry, DIMMER)

    await device.parse_lightlevel(SimpleNamespace(state=True, dim=128 * 256))
    state = hass.states.get(entity_id)
    assert state.state == "on"
    assert state.attributes["brightness"] == 128
    assert state.attributes["supported_color_modes"] == ["brightness"]

    await device.parse_lightlevel(SimpleNamespace(state=False, dim=0))
    assert hass.states.get(entity_id).state == "off"


async def test_light_brightness_is_kept_in_range(
    hass: HomeAssistant, loaded_entry: MockConfigEntry
) -> None:
    """Een te hoge waarde van het apparaat wordt begrensd tot 255."""
    entity_id = get_entity_id(hass, "light", DIMMER)
    push_state(get_device(loaded_entry, DIMMER), state=True, dim=300)

    assert hass.states.get(entity_id).attributes["brightness"] == 255


async def test_light_commands(
    hass: HomeAssistant, loaded_entry: MockConfigEntry
) -> None:
    """Aan, uit en helderheid worden naar het apparaat gestuurd."""
    entity_id = get_entity_id(hass, "light", DIMMER)

    with patch.object(PlejdLight, "turn_on", AsyncMock()) as turn_on:
        await hass.services.async_call(
            "light", "turn_on", {"entity_id": entity_id, "brightness": 100}, blocking=True
        )
    turn_on.assert_awaited_once_with(100, None)

    with patch.object(PlejdLight, "turn_off", AsyncMock()) as turn_off:
        await hass.services.async_call(
            "light", "turn_off", {"entity_id": entity_id}, blocking=True
        )
    turn_off.assert_awaited_once_with()


async def test_tunable_light(
    hass: HomeAssistant, loaded_entry: MockConfigEntry
) -> None:
    """Een lamp met instelbare kleurtemperatuur stuurt mired door aan pyplejd."""
    entity_id = get_entity_id(hass, "light", SPOT)
    device = get_device(loaded_entry, SPOT)
    await device.parse_lightlevel(SimpleNamespace(state=True, dim=200 * 256))
    push_state(device, colortemp=3000)

    state = hass.states.get(entity_id)
    assert state.attributes["supported_color_modes"] == ["color_temp"]
    assert state.attributes["min_color_temp_kelvin"] == 2200
    assert state.attributes["max_color_temp_kelvin"] == 4000
    assert state.attributes["color_temp_kelvin"] == 3000

    with patch.object(PlejdLight, "turn_on", AsyncMock()) as turn_on:
        await hass.services.async_call(
            "light",
            "turn_on",
            {"entity_id": entity_id, "color_temp_kelvin": 2500},
            blocking=True,
        )
    brightness, colortemp = turn_on.await_args.args
    assert brightness is None
    assert colortemp == pytest.approx(1e6 / 2500)


async def test_switch_follows_state_and_commands(
    hass: HomeAssistant, loaded_entry: MockConfigEntry
) -> None:
    """Een relais volgt zijn status en reageert op commando's."""
    entity_id = get_entity_id(hass, "switch", RELAY_A)
    assert hass.states.get(entity_id).state == "unknown"

    push_state(get_device(loaded_entry, RELAY_A), state=True)
    assert hass.states.get(entity_id).state == "on"

    with patch.object(PlejdRelay, "turn_off", AsyncMock()) as turn_off:
        await hass.services.async_call(
            "switch", "turn_off", {"entity_id": entity_id}, blocking=True
        )
    turn_off.assert_awaited_once_with()

    with patch.object(PlejdRelay, "turn_on", AsyncMock()) as turn_on:
        await hass.services.async_call(
            "switch", "turn_on", {"entity_id": entity_id}, blocking=True
        )
    turn_on.assert_awaited_once_with()


async def test_button_events(
    hass: HomeAssistant, loaded_entry: MockConfigEntry
) -> None:
    """Een knop meldt indrukken en loslaten, en negeert andere meldingen."""
    entity_id = get_entity_id(hass, "event", BUTTON_ENTITY)
    device = get_device(loaded_entry, BUTTON_DEVICE)
    assert hass.states.get(entity_id).attributes["friendly_name"] == (
        "WPH-01-LC Button 1"
    )

    push_update(device, {"button": 0, "action": "press"})
    assert hass.states.get(entity_id).attributes["event_type"] == "press"

    push_update(device, {"button": 0, "action": "release"})
    assert hass.states.get(entity_id).attributes["event_type"] == "release"

    push_update(device, {})
    assert hass.states.get(entity_id).attributes["event_type"] == "release"


async def test_motion_sensor(
    hass: HomeAssistant, loaded_entry: MockConfigEntry
) -> None:
    """De bewegingssensor onthoudt beweging tot hij meldt dat die voorbij is."""
    entity_id = get_entity_id(hass, "binary_sensor", MOTION)
    device = get_device(loaded_entry, MOTION)
    assert hass.states.get(entity_id).state == "off"
    assert "battery" not in hass.states.get(entity_id).attributes

    push_state(device, motion=True, battery=80, bright=True)
    state = hass.states.get(entity_id)
    assert state.state == "on"
    assert state.attributes["battery"] == 80
    assert state.attributes["bright"] is True

    push_state(device, motion=None)
    assert hass.states.get(entity_id).state == "on"

    push_state(device, motion=False)
    assert hass.states.get(entity_id).state == "off"


async def test_entities_become_unavailable_without_connection(
    hass: HomeAssistant, loaded_entry: MockConfigEntry, mocks: SimpleNamespace
) -> None:
    """Zonder Bluetooth-verbinding zijn alle entiteiten niet beschikbaar."""
    mocks.mesh.connected.return_value = False
    for device in loaded_entry.runtime_data.devices:
        device.set_available(False)
    await hass.async_block_till_done()

    for domain, unique_id in (
        ("light", DIMMER),
        ("switch", RELAY_A),
        ("event", BUTTON_ENTITY),
        ("binary_sensor", MOTION),
    ):
        state = hass.states.get(get_entity_id(hass, domain, unique_id))
        assert state.state == "unavailable"


async def test_commands_without_connection_give_a_clear_error(
    hass: HomeAssistant, loaded_entry: MockConfigEntry, mocks: SimpleNamespace
) -> None:
    """Zonder verbinding krijg je een foutmelding in plaats van stilte."""
    light = get_entity(hass, get_entity_id(hass, "light", DIMMER))
    switch = get_entity(hass, get_entity_id(hass, "switch", RELAY_A))
    mocks.mesh.connected.return_value = False

    for call in (
        light.async_turn_on(),
        light.async_turn_off(),
        switch.async_turn_on(),
        switch.async_turn_off(),
    ):
        with pytest.raises(HomeAssistantError):
            await call
