"""Tests voor fouten in de achtergrondtaken van de verbinding."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.core import HomeAssistant


async def test_error_during_the_keep_alive_is_caught(
    hass: HomeAssistant,
    loaded_entry: MockConfigEntry,
    mocks: SimpleNamespace,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Een fout bij de keep-alive stopt de taak niet en geeft één waarschuwing."""
    site = loaded_entry.runtime_data
    mocks.mesh.ping.side_effect = RuntimeError("kapot")
    mocks.mesh.disconnect.reset_mock()

    await site._async_ping()
    await site._async_ping()

    assert site.ping_failures == 2
    assert caplog.text.count("gaf een fout: kapot") == 1
    site._cancel_reconnect()
    site._cancel_reconnect = None


async def test_error_during_the_clock_check_is_caught(
    hass: HomeAssistant,
    loaded_entry: MockConfigEntry,
    mocks: SimpleNamespace,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Een fout bij de klokcontrole stopt de taak niet."""
    site = loaded_entry.runtime_data
    mocks.mesh.broadcast_time.side_effect = RuntimeError("geen klok")

    await site._async_broadcast_time()

    assert "klokcontrole van het Plejd-mesh mislukte: geen klok" in caplog.text
