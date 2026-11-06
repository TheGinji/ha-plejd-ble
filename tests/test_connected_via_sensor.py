"""Tests voor de sensor die laat zien via welk apparaat we verbonden zijn."""

from __future__ import annotations

from types import SimpleNamespace

from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.core import HomeAssistant

from . import DIMMER, get_device, get_entity_id
from .conftest import ENTRY_ID


async def test_connected_via_sensor_shows_the_unit(
    hass: HomeAssistant, loaded_entry: MockConfigEntry, mocks: SimpleNamespace
) -> None:
    """De sensor toont de naam van het apparaat, en niets zonder verbinding."""
    entity_id = get_entity_id(hass, "sensor", f"{ENTRY_ID}:connected_via")
    manager = loaded_entry.runtime_data.manager
    dimmer = get_device(loaded_entry, DIMMER)
    assert hass.states.get(entity_id).state == "unknown"

    manager.mesh._gateway_node = SimpleNamespace(BLEaddress=dimmer.BLEaddress)
    manager.connection_monitor(True)
    await hass.async_block_till_done()
    assert hass.states.get(entity_id).state == "Zithoek (Woonkamer)"

    mocks.mesh.connected.return_value = False
    manager.connection_monitor(False)
    await hass.async_block_till_done()
    assert hass.states.get(entity_id).state == "unknown"
