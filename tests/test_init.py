"""Tests voor het opstarten, de cache en het afsluiten van Plejd BLE."""

from __future__ import annotations

from collections.abc import Callable
from datetime import timedelta
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

from pyplejd import PLEJD_SERVICE, AuthenticationError, ConnectionError as PlejdConnectionError
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import (
    area_registry as ar,
    device_registry as dr,
    entity_registry as er,
)
from homeassistant.util import dt as dt_util

from custom_components.plejd_ble import async_remove_config_entry_device
from custom_components.plejd_ble.const import DOMAIN

from . import NUMBER_OF_ENTITIES, setup_integration
from .conftest import STORE_KEY


async def test_fresh_cache_does_not_use_the_cloud(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    store_cache: Callable[[timedelta], None],
    mocks: SimpleNamespace,
) -> None:
    """Met een verse cache wordt de Plejd-cloud niet aangeroepen."""
    store_cache(timedelta(days=1))
    await setup_integration(hass, config_entry)

    assert config_entry.state is ConfigEntryState.LOADED
    mocks.cloud.assert_not_awaited()
    assert config_entry.runtime_data.used_cloud is False


async def test_missing_cache_fetches_and_saves(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    mocks: SimpleNamespace,
    hass_storage: dict[str, Any],
) -> None:
    """Zonder cache halen we de gegevens één keer op en bewaren we ze."""
    await setup_integration(hass, config_entry)

    assert config_entry.state is ConfigEntryState.LOADED
    mocks.cloud.assert_awaited_once()
    assert config_entry.runtime_data.used_cloud is True
    saved = hass_storage[STORE_KEY]["data"]
    assert saved["data"]["site"]["siteId"] == "site-1"
    fetched_at = dt_util.parse_datetime(saved["fetched_at"])
    assert dt_util.utcnow() - fetched_at < timedelta(minutes=1)


async def test_stale_cache_is_refreshed(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    store_cache: Callable[[timedelta], None],
    mocks: SimpleNamespace,
    hass_storage: dict[str, Any],
) -> None:
    """Een cache van meer dan zeven dagen oud wordt vernieuwd."""
    store_cache(timedelta(days=8))
    await setup_integration(hass, config_entry)

    assert config_entry.state is ConfigEntryState.LOADED
    mocks.cloud.assert_awaited_once()
    fetched_at = dt_util.parse_datetime(hass_storage[STORE_KEY]["data"]["fetched_at"])
    assert dt_util.utcnow() - fetched_at < timedelta(minutes=1)


async def test_cloud_down_falls_back_to_old_cache(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    store_cache: Callable[[timedelta], None],
    mocks: SimpleNamespace,
) -> None:
    """Is de cloud onbereikbaar, dan werkt de integratie met de oude cache."""
    store_cache(timedelta(days=30))
    mocks.cloud.side_effect = PlejdConnectionError
    await setup_integration(hass, config_entry)

    assert config_entry.state is ConfigEntryState.LOADED
    assert config_entry.runtime_data.used_cloud is False


async def test_cloud_down_without_cache_retries_later(
    hass: HomeAssistant, config_entry: MockConfigEntry, mocks: SimpleNamespace
) -> None:
    """Zonder cache en zonder cloud proberen we het later opnieuw."""
    mocks.cloud.side_effect = PlejdConnectionError
    await setup_integration(hass, config_entry)

    assert config_entry.state is ConfigEntryState.SETUP_RETRY


async def test_wrong_login_starts_reauth(
    hass: HomeAssistant, config_entry: MockConfigEntry, mocks: SimpleNamespace
) -> None:
    """Weigert de cloud de inlog, dan vraagt Home Assistant om opnieuw in te loggen."""
    mocks.cloud.side_effect = AuthenticationError
    await setup_integration(hass, config_entry)

    assert config_entry.state is ConfigEntryState.SETUP_ERROR
    flows = hass.config_entries.flow.async_progress_by_handler(DOMAIN)
    assert any(flow["context"]["source"] == "reauth" for flow in flows)


async def test_only_useful_entities_are_created(
    hass: HomeAssistant, loaded_entry: MockConfigEntry
) -> None:
    """Er zijn geen diagnose-entiteiten, en verborgen apparaten ontbreken."""
    entities = er.async_entries_for_config_entry(
        er.async_get(hass), loaded_entry.entry_id
    )

    assert len(entities) == NUMBER_OF_ENTITIES
    assert {entity.domain for entity in entities} == {
        "light",
        "switch",
        "event",
        "binary_sensor",
    }


async def test_devices_have_clear_names(
    hass: HomeAssistant, loaded_entry: MockConfigEntry
) -> None:
    """Dubbele en lege namen worden duidelijk gemaakt."""
    devices = dr.async_entries_for_config_entry(
        dr.async_get(hass), loaded_entry.entry_id
    )

    assert {device.name for device in devices} == {
        "Zithoek",
        "Slaapkamer 1 Plafondlicht",
        "Slaapkamer 2 Plafondlicht",
        "Spot",
        "Wandlamp",
        "Tuinlamp",
        "Hal WPH-01-LC",
        "Beweging toilet",
    }


async def test_device_hierarchy_and_details(
    hass: HomeAssistant, loaded_entry: MockConfigEntry
) -> None:
    """De tweede uitgang van een relais hoort onder de eerste."""
    registry = dr.async_get(hass)
    first = registry.async_get_device(identifiers={(DOMAIN, "A0B1C2000005:dev-rel-a")})
    second = registry.async_get_device(identifiers={(DOMAIN, "A0B1C2000005:dev-rel-b")})

    assert first is not None
    assert second is not None
    assert first.via_device_id is None
    assert second.via_device_id == first.id
    assert first.model == "REL-01-2P"
    assert first.manufacturer == "Plejd"
    assert first.sw_version == "1.2.3"
    area = ar.async_get(hass).async_get_area_by_name("Woonkamer")
    assert area is not None
    assert first.area_id == area.id


async def test_unload_disconnects(
    hass: HomeAssistant, loaded_entry: MockConfigEntry, mocks: SimpleNamespace
) -> None:
    """Bij verwijderen wordt de Bluetooth-verbinding verbroken."""
    assert await hass.config_entries.async_unload(loaded_entry.entry_id)

    assert loaded_entry.state is ConfigEntryState.NOT_LOADED
    mocks.mesh.disconnect.assert_awaited()


async def test_remove_device(
    hass: HomeAssistant, loaded_entry: MockConfigEntry
) -> None:
    """Alleen apparaten die niet meer in de site zitten mogen weg."""
    registry = dr.async_get(hass)
    active = registry.async_get_device(identifiers={(DOMAIN, "A0B1C2000001:dev-dimmer")})
    orphan = registry.async_get_or_create(
        config_entry_id=loaded_entry.entry_id, identifiers={(DOMAIN, "weesapparaat")}
    )

    assert not await async_remove_config_entry_device(hass, loaded_entry, active)
    assert await async_remove_config_entry_device(hass, loaded_entry, orphan)


async def test_start_connects_once(
    hass: HomeAssistant, loaded_entry: MockConfigEntry, mocks: SimpleNamespace
) -> None:
    """Bij het starten wordt er één keer verbonden en de klok gecontroleerd."""
    mocks.mesh.ping.assert_awaited_once()
    mocks.mesh.broadcast_time.assert_awaited_once()


async def test_stale_connections_are_closed(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    store_cache: Callable[[timedelta], None],
    mocks: SimpleNamespace,
) -> None:
    """Oude verbindingen worden gesloten, één keer per fysiek apparaat."""
    store_cache(timedelta(hours=1))
    mocks.bluetooth.ble_device.return_value = MagicMock()
    await setup_integration(hass, config_entry)

    assert mocks.mesh.close_stale.await_count == 7


async def test_discovered_plejd_triggers_connection(
    hass: HomeAssistant, loaded_entry: MockConfigEntry, mocks: SimpleNamespace
) -> None:
    """Een nieuw gevonden Plejd-apparaat zorgt voor een verbindingspoging."""
    callback = mocks.bluetooth.register_callback.call_args.args[1]
    service_info = SimpleNamespace(
        device=SimpleNamespace(address="A0:B1:C2:00:00:01", name="Plejd"), rssi=-60
    )
    assert mocks.mesh.ping.await_count == 1

    callback(service_info, None)
    await hass.async_block_till_done()
    assert mocks.mesh.ping.await_count == 2

    callback(service_info, None)
    await hass.async_block_till_done()
    assert mocks.mesh.ping.await_count == 2


async def test_already_discovered_plejd_does_not_reconnect(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    store_cache: Callable[[timedelta], None],
    mocks: SimpleNamespace,
) -> None:
    """Apparaten die al bekend zijn bij het starten geven geen extra verbinding."""
    store_cache(timedelta(hours=1))
    mocks.bluetooth.discovered.return_value = [
        SimpleNamespace(
            device=SimpleNamespace(address="A0:B1:C2:00:00:02", name="Plejd"),
            rssi=-70,
            advertisement=SimpleNamespace(service_uuids=[PLEJD_SERVICE.lower()]),
        ),
        SimpleNamespace(
            device=SimpleNamespace(address="11:22:33:44:55:66", name="Iets anders"),
            rssi=-40,
            advertisement=SimpleNamespace(service_uuids=["0000180f-0000-1000-8000-00805f9b34fb"]),
        ),
    ]
    await setup_integration(hass, config_entry)

    assert config_entry.state is ConfigEntryState.LOADED
    mocks.mesh.ping.assert_awaited_once()


async def test_lost_connection_reconnects(
    hass: HomeAssistant, loaded_entry: MockConfigEntry, mocks: SimpleNamespace
) -> None:
    """Valt de verbinding weg, dan wordt opnieuw verbonden."""
    monitor = loaded_entry.runtime_data.manager.connection_monitor

    monitor(True)
    await hass.async_block_till_done()
    assert mocks.mesh.ping.await_count == 1

    monitor(False)
    await hass.async_block_till_done()
    assert mocks.mesh.ping.await_count == 2


async def test_periodic_keep_alive_and_clock_check(
    hass: HomeAssistant, loaded_entry: MockConfigEntry, mocks: SimpleNamespace
) -> None:
    """De verbinding wordt elke paar minuten bewaakt en de klok elk uur."""
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(minutes=4))
    await hass.async_block_till_done()
    assert mocks.mesh.ping.await_count == 2
    assert mocks.mesh.broadcast_time.await_count == 1

    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(hours=1, minutes=5))
    await hass.async_block_till_done()
    assert mocks.mesh.ping.await_count == 3
    assert mocks.mesh.broadcast_time.await_count == 2


async def test_failed_ping_does_not_break_setup(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    store_cache: Callable[[timedelta], None],
    mocks: SimpleNamespace,
) -> None:
    """Een mislukte verbindingspoging mag het opstarten niet blokkeren."""
    store_cache(timedelta(hours=1))
    mocks.mesh.ping.return_value = False
    await setup_integration(hass, config_entry)

    assert config_entry.state is ConfigEntryState.LOADED


async def test_home_assistant_stopping_stops_everything(
    hass: HomeAssistant, loaded_entry: MockConfigEntry, mocks: SimpleNamespace
) -> None:
    """Stopt Home Assistant, dan verbreken we de verbinding en doen we niets meer."""
    site = loaded_entry.runtime_data

    await site.async_hass_stopping(None)

    mocks.mesh.disconnect.assert_awaited_once()
    await site._async_ping()
    await site._async_broadcast_time()
    assert mocks.mesh.ping.await_count == 1
    assert mocks.mesh.broadcast_time.await_count == 1
