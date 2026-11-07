"""Tests voor een verbinding die open lijkt maar niet meer antwoordt."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.core import HomeAssistant


async def test_dead_connection_is_dropped_so_it_gets_rebuilt(
    hass: HomeAssistant,
    loaded_entry: MockConfigEntry,
    mocks: SimpleNamespace,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Antwoordt een open verbinding niet, dan verbreken we hem, met een waarschuwing."""
    site = loaded_entry.runtime_data
    mocks.mesh.ping.return_value = False
    mocks.mesh.disconnect.reset_mock()

    await site._async_ping()

    assert mocks.mesh.disconnect.await_count == 1
    assert "reageert niet meer" in caplog.text
    site._cancel_reconnect()
    site._cancel_reconnect = None


async def test_failed_ping_without_a_connection_does_not_disconnect(
    hass: HomeAssistant, loaded_entry: MockConfigEntry, mocks: SimpleNamespace
) -> None:
    """Is er geen verbinding, dan valt er ook niets te verbreken."""
    site = loaded_entry.runtime_data
    mocks.mesh.connected.return_value = False
    mocks.mesh.ping.return_value = False
    mocks.mesh.disconnect.reset_mock()

    await site._async_ping()

    assert mocks.mesh.disconnect.await_count == 0
    site._cancel_reconnect()
    site._cancel_reconnect = None
