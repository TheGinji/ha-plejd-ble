"""Tests voor het bewaren van de kleurtemperatuur van lampen."""

from __future__ import annotations

from types import SimpleNamespace

from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    mock_restore_cache_with_extra_data,
)

from homeassistant.core import HomeAssistant, State

from . import (
    DIMMER,
    SPOT,
    get_device,
    get_entity,
    get_entity_id,
    push_state,
    setup_entry,
)


async def test_color_temperature_is_restored_after_a_restart(
    hass: HomeAssistant, loaded_entry: MockConfigEntry
) -> None:
    """Plejd meldt de kleurtemperatuur alleen als hij verandert, dus we bewaren hem."""
    entity_id = get_entity_id(hass, "light", SPOT)
    assert await hass.config_entries.async_unload(loaded_entry.entry_id)
    # De lamp stond uit toen Home Assistant stopte: de waarde blijft toch bewaard.
    mock_restore_cache_with_extra_data(
        hass, ((State(entity_id, "off"), {"color_temp_kelvin": 2700}),)
    )

    await setup_entry(hass, loaded_entry)
    device = get_device(loaded_entry, SPOT)
    await device.parse_lightlevel(SimpleNamespace(state=True, dim=200 * 256))

    assert hass.states.get(entity_id).attributes["color_temp_kelvin"] == 2700

    push_state(device, colortemp=3000)
    assert hass.states.get(entity_id).attributes["color_temp_kelvin"] == 3000


async def test_only_tunable_lights_keep_a_color_temperature(
    hass: HomeAssistant, loaded_entry: MockConfigEntry
) -> None:
    """Een dimmer zonder kleurtemperatuur bewaart er geen."""
    tunable = get_entity(hass, get_entity_id(hass, "light", SPOT))
    plain = get_entity(hass, get_entity_id(hass, "light", DIMMER))
    push_state(get_device(loaded_entry, SPOT), colortemp=3000)

    assert tunable.extra_restore_state_data.as_dict() == {"color_temp_kelvin": 3000}
    assert plain.extra_restore_state_data is None
