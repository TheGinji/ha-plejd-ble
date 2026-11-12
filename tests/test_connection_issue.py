"""Tests voor de melding in Herstelacties als de verbinding wegblijft."""

from __future__ import annotations

from datetime import timedelta
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, patch

from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)

from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir
from homeassistant.util import dt as dt_util

from custom_components.plejd_ble.const import DOMAIN

from .conftest import ENTRY_ID

ISSUE_ID = f"mesh_disconnected_{ENTRY_ID}"


async def advance(hass: HomeAssistant, seconds: int) -> None:
    """Laat de tijd vooruitlopen en wacht tot alles is afgehandeld."""
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=seconds))
    await hass.async_block_till_done()


def lose_connection(site: Any, mocks: SimpleNamespace) -> None:
    """Doe alsof de verbinding met het mesh wegvalt, zoals pyplejd dat meldt."""
    mocks.mesh.connected.return_value = False
    site.manager.connection_monitor(False)


def restore_connection(site: Any, mocks: SimpleNamespace) -> None:
    """Doe alsof de verbinding met het mesh terug is."""
    mocks.mesh.connected.return_value = True
    site.manager.connection_monitor(True)


def get_issue(hass: HomeAssistant) -> ir.IssueEntry | None:
    """Geef de melding, of niets."""
    return ir.async_get(hass).async_get_issue(DOMAIN, ISSUE_ID)


async def test_issue_appears_when_the_connection_stays_away(
    hass: HomeAssistant, loaded_entry: MockConfigEntry, mocks: SimpleNamespace
) -> None:
    """Na vijf minuten zonder verbinding staat er een melding in Herstelacties."""
    lose_connection(loaded_entry.runtime_data, mocks)

    await advance(hass, 200)
    assert get_issue(hass) is None

    await advance(hass, 330)
    issue = get_issue(hass)
    assert issue is not None
    assert issue.severity is ir.IssueSeverity.WARNING
    assert issue.is_fixable is False
    assert issue.translation_key == "mesh_disconnected"


async def test_no_issue_when_the_connection_returns_in_time(
    hass: HomeAssistant, loaded_entry: MockConfigEntry, mocks: SimpleNamespace
) -> None:
    """Een korte onderbreking, zoals een herstel van een minuut, geeft geen melding."""
    site = loaded_entry.runtime_data
    lose_connection(site, mocks)
    await advance(hass, 60)
    restore_connection(site, mocks)

    await advance(hass, 400)

    assert get_issue(hass) is None


async def test_no_issue_when_connected_at_the_end_of_the_wait(
    hass: HomeAssistant, loaded_entry: MockConfigEntry
) -> None:
    """Is er na de wachttijd toch verbinding, dan maken we geen melding."""
    await advance(hass, 400)

    assert get_issue(hass) is None


async def test_issue_disappears_when_the_connection_returns(
    hass: HomeAssistant, loaded_entry: MockConfigEntry, mocks: SimpleNamespace
) -> None:
    """Zodra de verbinding terug is, verdwijnt de melding vanzelf."""
    site = loaded_entry.runtime_data
    lose_connection(site, mocks)
    await advance(hass, 330)
    assert get_issue(hass) is not None

    restore_connection(site, mocks)

    assert get_issue(hass) is None


async def test_removing_the_entry_removes_the_issue(
    hass: HomeAssistant, loaded_entry: MockConfigEntry, mocks: SimpleNamespace
) -> None:
    """Verwijderen van de integratie laat geen melding achter."""
    lose_connection(loaded_entry.runtime_data, mocks)
    await advance(hass, 330)
    assert get_issue(hass) is not None

    with patch(
        "homeassistant.helpers.storage.Store.async_remove", new_callable=AsyncMock
    ):
        assert await hass.config_entries.async_remove(loaded_entry.entry_id)
        await hass.async_block_till_done()

    assert get_issue(hass) is None


async def test_stopping_cancels_the_pending_wait(
    hass: HomeAssistant, loaded_entry: MockConfigEntry, mocks: SimpleNamespace
) -> None:
    """Stopt Home Assistant, dan komt er ook geen melding meer."""
    site = loaded_entry.runtime_data
    lose_connection(site, mocks)

    await site.async_hass_stopping(None)
    await advance(hass, 400)

    assert get_issue(hass) is None
