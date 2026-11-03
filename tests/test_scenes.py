"""Tests voor de Plejd-scènes."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from pyplejd.interface.plejd_scene import PlejdScene
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er

from custom_components.plejd_ble.const import DOMAIN

from . import get_entity, get_entity_id
from .conftest import ENTRY_ID

VISIBLE_SCENE = f"{ENTRY_ID}:scene:scene-1"
HIDDEN_SCENE = f"{ENTRY_ID}:scene:scene-2"


async def test_only_visible_scenes_are_created(
    hass: HomeAssistant, loaded_entry: MockConfigEntry
) -> None:
    """Scènes die Plejd verbergt, krijgen geen entiteit."""
    entity_id = get_entity_id(hass, "scene", VISIBLE_SCENE)

    assert hass.states.get(entity_id).attributes["friendly_name"] == "Avond"
    assert er.async_get(hass).async_get_entity_id("scene", DOMAIN, HIDDEN_SCENE) is None


async def test_activating_a_scene_sends_one_message(
    hass: HomeAssistant, loaded_entry: MockConfigEntry
) -> None:
    """Een scène activeren is één opdracht aan het mesh."""
    entity_id = get_entity_id(hass, "scene", VISIBLE_SCENE)

    with patch.object(PlejdScene, "activate", AsyncMock()) as activate:
        await hass.services.async_call(
            "scene", "turn_on", {"entity_id": entity_id}, blocking=True
        )

    activate.assert_awaited_once_with()


async def test_scene_is_unavailable_without_connection(
    hass: HomeAssistant, loaded_entry: MockConfigEntry, mocks: SimpleNamespace
) -> None:
    """Zonder Bluetooth-verbinding is de scène niet beschikbaar en geeft activeren een fout."""
    entity_id = get_entity_id(hass, "scene", VISIBLE_SCENE)
    monitor = loaded_entry.runtime_data.manager.connection_monitor
    assert hass.states.get(entity_id).state != "unavailable"

    mocks.mesh.connected.return_value = False
    monitor(False)
    await hass.async_block_till_done()

    assert hass.states.get(entity_id).state == "unavailable"
    with pytest.raises(HomeAssistantError):
        await get_entity(hass, entity_id).async_activate()
