"""Tests voor de verversknop, de diagnosesensor en de reparatiemelding."""

from __future__ import annotations

from collections.abc import Callable
from datetime import timedelta
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, patch

from pyplejd import ConnectionError as PlejdConnectionError
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er, issue_registry as ir
from homeassistant.util import dt as dt_util

from custom_components.plejd_ble import async_remove_config_entry_device
from custom_components.plejd_ble.const import DOMAIN

from . import get_device_entry, get_entity_id, setup_integration
from .conftest import ENTRY_ID, STORE_KEY

ISSUE_ID = f"cloud_unreachable_{ENTRY_ID}"


async def test_refresh_button_fetches_a_new_device_list(
    hass: HomeAssistant,
    loaded_entry: MockConfigEntry,
    mocks: SimpleNamespace,
    hass_storage: dict[str, Any],
) -> None:
    """De knop haalt de lijst opnieuw uit de cloud en laadt de integratie opnieuw."""
    button = get_entity_id(hass, "button", f"{ENTRY_ID}:refresh_cloud")
    mocks.cloud.assert_not_awaited()

    await hass.services.async_call(
        "button", "press", {"entity_id": button}, blocking=True
    )
    await hass.async_block_till_done()

    mocks.cloud.assert_awaited_once()
    assert loaded_entry.state is ConfigEntryState.LOADED
    assert loaded_entry.runtime_data.used_cloud is True
    saved = hass_storage[STORE_KEY]["data"]
    fetched_at = dt_util.parse_datetime(saved["fetched_at"])
    assert dt_util.utcnow() - fetched_at < timedelta(minutes=1)
    assert "refresh_requested" not in saved


async def test_refresh_keeps_the_old_list_when_the_cloud_is_down(
    hass: HomeAssistant, loaded_entry: MockConfigEntry, mocks: SimpleNamespace
) -> None:
    """Is de cloud weg tijdens verversen, dan blijft de oude lijst bruikbaar."""
    button = get_entity_id(hass, "button", f"{ENTRY_ID}:refresh_cloud")
    mocks.cloud.side_effect = PlejdConnectionError

    await hass.services.async_call(
        "button", "press", {"entity_id": button}, blocking=True
    )
    await hass.async_block_till_done()

    assert loaded_entry.state is ConfigEntryState.LOADED
    assert loaded_entry.runtime_data.used_cloud is False
    assert ir.async_get(hass).async_get_issue(DOMAIN, ISSUE_ID) is None


async def test_last_sync_sensor_is_disabled_by_default(
    hass: HomeAssistant, loaded_entry: MockConfigEntry
) -> None:
    """De diagnosesensor staat standaard uit."""
    entity_id = get_entity_id(hass, "sensor", f"{ENTRY_ID}:last_cloud_sync")

    entry = er.async_get(hass).async_get(entity_id)
    assert entry.disabled_by is er.RegistryEntryDisabler.INTEGRATION
    assert hass.states.get(entity_id) is None


async def test_last_sync_sensor_shows_the_time_when_enabled(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    store_cache: Callable[[timedelta], None],
    mocks: SimpleNamespace,
) -> None:
    """Staat de sensor aan, dan toont hij wanneer de lijst is opgehaald."""
    store_cache(timedelta(hours=3))
    config_entry.add_to_hass(hass)
    registry = er.async_get(hass)
    registry.async_get_or_create(
        "sensor", DOMAIN, f"{ENTRY_ID}:last_cloud_sync", config_entry=config_entry
    )
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get(get_entity_id(hass, "sensor", f"{ENTRY_ID}:last_cloud_sync"))
    shown = dt_util.parse_datetime(state.state)
    expected = dt_util.utcnow() - timedelta(hours=3)
    assert abs(shown - expected) < timedelta(minutes=1)


async def test_old_cache_without_cloud_creates_a_repair_issue(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    store_cache: Callable[[timedelta], None],
    mocks: SimpleNamespace,
) -> None:
    """Een lijst die al weken oud is en niet ververst kan worden, geeft een melding."""
    store_cache(timedelta(days=30))
    mocks.cloud.side_effect = PlejdConnectionError
    await setup_integration(hass, config_entry)

    issue = ir.async_get(hass).async_get_issue(DOMAIN, ISSUE_ID)
    assert issue is not None
    assert issue.severity is ir.IssueSeverity.WARNING
    assert issue.is_fixable is False
    assert issue.translation_key == "cloud_unreachable"

    with patch(
        "homeassistant.helpers.storage.Store.async_remove", new_callable=AsyncMock
    ):
        assert await hass.config_entries.async_remove(config_entry.entry_id)
        await hass.async_block_till_done()
    assert ir.async_get(hass).async_get_issue(DOMAIN, ISSUE_ID) is None


async def test_successful_refresh_removes_the_repair_issue(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    store_cache: Callable[[timedelta], None],
    mocks: SimpleNamespace,
) -> None:
    """Lukt het ophalen weer, dan verdwijnt de melding."""
    store_cache(timedelta(days=30))
    ir.async_create_issue(
        hass,
        DOMAIN,
        ISSUE_ID,
        is_fixable=False,
        severity=ir.IssueSeverity.WARNING,
        translation_key="cloud_unreachable",
    )
    await setup_integration(hass, config_entry)

    assert ir.async_get(hass).async_get_issue(DOMAIN, ISSUE_ID) is None


async def test_fresh_cache_has_no_repair_issue(
    hass: HomeAssistant, loaded_entry: MockConfigEntry
) -> None:
    """Met een verse lijst is er niets aan de hand."""
    assert ir.async_get(hass).async_get_issue(DOMAIN, ISSUE_ID) is None


async def test_the_site_device_cannot_be_removed(
    hass: HomeAssistant, loaded_entry: MockConfigEntry
) -> None:
    """Het apparaat van de site zelf blijft bestaan zolang de integratie draait."""
    hub = get_device_entry(hass, loaded_entry, ENTRY_ID)

    assert hub is not None
    assert not await async_remove_config_entry_device(hass, loaded_entry, hub)
