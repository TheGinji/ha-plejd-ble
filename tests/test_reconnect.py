"""Tests voor sneller opnieuw verbinden na een mislukte poging."""

from __future__ import annotations

from collections.abc import Callable
from datetime import timedelta
import logging
from types import SimpleNamespace

import pytest
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)

from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from . import setup_integration


async def advance(hass: HomeAssistant, seconds: int) -> None:
    """Laat de tijd vooruitlopen en wacht tot alles is afgehandeld."""
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=seconds))
    await hass.async_block_till_done()


async def test_failed_connection_is_retried_soon(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    store_cache: Callable[[timedelta], None],
    mocks: SimpleNamespace,
) -> None:
    """Na een mislukte eerste poging proberen we het snel opnieuw, niet pas na drie minuten."""
    store_cache(timedelta(hours=1))
    mocks.mesh.ping.return_value = False
    await setup_integration(hass, config_entry)
    assert mocks.mesh.ping.await_count == 1

    await advance(hass, 11)
    assert mocks.mesh.ping.await_count == 2

    mocks.mesh.ping.return_value = True
    await advance(hass, 45)
    assert mocks.mesh.ping.await_count == 3

    await advance(hass, 100)
    assert mocks.mesh.ping.await_count == 3


async def test_one_warning_when_there_is_still_no_connection(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    store_cache: Callable[[timedelta], None],
    mocks: SimpleNamespace,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Na twee mislukte pogingen staat er één waarschuwing, en na herstel een melding."""
    caplog.set_level(logging.INFO, logger="custom_components.plejd_ble.site")
    store_cache(timedelta(hours=1))
    mocks.mesh.ping.return_value = False
    await setup_integration(hass, config_entry)
    assert "Geen verbinding met het Plejd-mesh" not in caplog.text

    await advance(hass, 11)
    assert caplog.text.count("Geen verbinding met het Plejd-mesh") == 1
    assert "0 van de 5 apparaten" in caplog.text

    await advance(hass, 45)
    assert mocks.mesh.ping.await_count == 3
    assert caplog.text.count("Geen verbinding met het Plejd-mesh") == 1

    mocks.mesh.ping.return_value = True
    await advance(hass, 100)
    assert "De verbinding met het Plejd-mesh is hersteld" in caplog.text


async def test_retry_stops_when_the_integration_is_unloaded(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    store_cache: Callable[[timedelta], None],
    mocks: SimpleNamespace,
) -> None:
    """Een geplande nieuwe poging vervalt als de integratie wordt uitgeladen."""
    store_cache(timedelta(hours=1))
    mocks.mesh.ping.return_value = False
    await setup_integration(hass, config_entry)
    assert mocks.mesh.ping.await_count == 1

    assert await hass.config_entries.async_unload(config_entry.entry_id)
    await advance(hass, 60)

    assert mocks.mesh.ping.await_count == 1
