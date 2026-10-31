"""Tests voor het verversen van de apparatenlijst: herstart, herladen en de knop."""

from __future__ import annotations

import copy
from datetime import timedelta
from types import SimpleNamespace
from typing import Any

from pyplejd import ConnectionError as PlejdConnectionError
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util

from custom_components.plejd_ble.const import DOMAIN

from . import SPOT, get_entity_id, setup_integration
from .conftest import ENTRY_ID, STORE_KEY

SPOT_DEVICE_ID = "A0B1C2000004"


def spot_entity_id(hass: HomeAssistant) -> str | None:
    """Geef het entiteit-ID van de spot, of niets als die er niet is."""
    return er.async_get(hass).async_get_entity_id("light", DOMAIN, SPOT)


@pytest.fixture
def cache_without_spot(
    hass_storage: dict[str, Any], site_data: dict[str, Any]
) -> None:
    """Bewaar een vers uur oude lijst waarin de spot nog niet staat.

    Dit lijkt op de situatie waarin iemand een lamp aan de Plejd-app toevoegt
    nadat Home Assistant de lijst heeft opgehaald.
    """
    data = copy.deepcopy(site_data)
    for key in ("devices", "plejdDevices", "outputSettings"):
        data[key] = [item for item in data[key] if item["deviceId"] != SPOT_DEVICE_ID]
    for key in ("deviceAddress", "outputAddress"):
        del data[key][SPOT_DEVICE_ID]
    fetched_at = dt_util.utcnow() - timedelta(hours=1)
    hass_storage[STORE_KEY] = {
        "version": 1,
        "minor_version": 1,
        "key": STORE_KEY,
        "data": {"fetched_at": fetched_at.isoformat(), "data": data},
    }


async def test_restart_uses_the_saved_list(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    cache_without_spot: None,
    mocks: SimpleNamespace,
) -> None:
    """Bij een herstart blijft de bewaarde lijst in gebruik, zonder cloud."""
    await setup_integration(hass, config_entry)

    mocks.cloud.assert_not_awaited()
    assert spot_entity_id(hass) is None


async def test_reload_picks_up_a_new_device(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    cache_without_spot: None,
    mocks: SimpleNamespace,
) -> None:
    """Een herlaadbeurt haalt de lijst vers op, dus een nieuwe lamp verschijnt."""
    await setup_integration(hass, config_entry)
    assert spot_entity_id(hass) is None

    assert await hass.config_entries.async_reload(config_entry.entry_id)
    await hass.async_block_till_done()

    mocks.cloud.assert_awaited_once()
    assert config_entry.state is ConfigEntryState.LOADED
    assert spot_entity_id(hass) is not None


async def test_refresh_button_picks_up_a_new_device(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    cache_without_spot: None,
    mocks: SimpleNamespace,
) -> None:
    """De verversknop doet hetzelfde als een herlaadbeurt."""
    await setup_integration(hass, config_entry)
    button = get_entity_id(hass, "button", f"{ENTRY_ID}:refresh_cloud")

    await hass.services.async_call(
        "button", "press", {"entity_id": button}, blocking=True
    )
    await hass.async_block_till_done()

    mocks.cloud.assert_awaited_once()
    assert spot_entity_id(hass) is not None


async def test_reload_without_cloud_keeps_the_saved_list(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    cache_without_spot: None,
    mocks: SimpleNamespace,
) -> None:
    """Is de cloud er niet, dan blijft een herlaadbeurt gewoon werken."""
    await setup_integration(hass, config_entry)
    mocks.cloud.side_effect = PlejdConnectionError

    assert await hass.config_entries.async_reload(config_entry.entry_id)
    await hass.async_block_till_done()

    assert config_entry.state is ConfigEntryState.LOADED
    assert config_entry.runtime_data.used_cloud is False
    assert spot_entity_id(hass) is None
