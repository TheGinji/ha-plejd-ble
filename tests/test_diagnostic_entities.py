"""Tests voor de verbindingssensor, het batterijniveau en de signaalsensoren."""

from __future__ import annotations

from collections.abc import Callable
from datetime import timedelta
from types import SimpleNamespace

from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
    mock_restore_cache_with_extra_data,
)

from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, State
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util

from custom_components.plejd_ble.const import DOMAIN
from custom_components.plejd_ble.diagnostics import async_get_config_entry_diagnostics

from . import (
    DIMMER,
    MOTION,
    NUMBER_OF_ENABLED_ENTITIES,
    get_device,
    get_entity_id,
    push_state,
    setup_entry,
    setup_integration,
)
from .conftest import ENTRY_ID

MESH_CONNECTED = f"{ENTRY_ID}:mesh_connected"
POWERED_UNITS = ["A0B1C2000001:O:0", "A0B1C2000002:O:0", "A0B1C2000003:O:0", "A0B1C2000004:O:0", "A0B1C2000005:O:0"]


def service_info(address: str = "A0:B1:C2:00:00:01", rssi: int = -61) -> SimpleNamespace:
    """Maak een verzonnen Bluetooth-melding van een Plejd-apparaat."""
    return SimpleNamespace(device=SimpleNamespace(address=address, name="Plejd"), rssi=rssi)


async def test_only_the_useful_entities_are_enabled(
    hass: HomeAssistant, loaded_entry: MockConfigEntry
) -> None:
    """Diagnose per apparaat bestaat wel, maar staat standaard uit."""
    entries = er.async_entries_for_config_entry(er.async_get(hass), loaded_entry.entry_id)

    enabled = [entry for entry in entries if entry.disabled_by is None]
    disabled = [entry for entry in entries if entry.disabled_by is not None]
    assert len(enabled) == NUMBER_OF_ENABLED_ENTITIES
    assert len(disabled) == len(entries) - NUMBER_OF_ENABLED_ENTITIES
    assert all(entry.entity_category is EntityCategory.DIAGNOSTIC for entry in disabled)


async def test_mesh_sensor_follows_the_connection(
    hass: HomeAssistant, loaded_entry: MockConfigEntry, mocks: SimpleNamespace
) -> None:
    """De verbindingssensor laat zien of Home Assistant met het mesh verbonden is."""
    entity_id = get_entity_id(hass, "binary_sensor", MESH_CONNECTED)
    monitor = loaded_entry.runtime_data.manager.connection_monitor
    assert hass.states.get(entity_id).state == "on"

    mocks.mesh.connected.return_value = False
    monitor(False)
    await hass.async_block_till_done()
    assert hass.states.get(entity_id).state == "off"

    mocks.mesh.connected.return_value = True
    monitor(True)
    await hass.async_block_till_done()
    assert hass.states.get(entity_id).state == "on"


async def test_mesh_sensor_shows_the_active_gateway(
    hass: HomeAssistant, loaded_entry: MockConfigEntry
) -> None:
    """Het apparaat waarlangs we verbonden zijn, staat bij de sensor."""
    entity_id = get_entity_id(hass, "binary_sensor", MESH_CONNECTED)
    monitor = loaded_entry.runtime_data.manager.connection_monitor
    dimmer = get_device(loaded_entry, DIMMER)
    assert "connected_via" not in hass.states.get(entity_id).attributes

    dimmer.hw.is_gateway = True
    monitor(True)
    await hass.async_block_till_done()
    assert hass.states.get(entity_id).attributes["connected_via"] == "Zithoek (Woonkamer)"

    dimmer.hw.is_gateway = False
    monitor(True)
    await hass.async_block_till_done()
    assert "connected_via" not in hass.states.get(entity_id).attributes


async def test_connection_history_is_kept_for_diagnostics(
    hass: HomeAssistant, loaded_entry: MockConfigEntry, mocks: SimpleNamespace
) -> None:
    """Verbindingswijzigingen en mislukte pogingen komen in de diagnostische gegevens."""
    site = loaded_entry.runtime_data
    site.manager.connection_monitor(False)
    site.manager.connection_monitor(True)
    await hass.async_block_till_done()

    result = await async_get_config_entry_diagnostics(hass, loaded_entry)

    events = result["connection"]["recent_events"]
    assert [event["connected"] for event in events] == [False, True]
    assert all(dt_util.parse_datetime(event["at"]) for event in events)


async def test_failed_pings_are_counted(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    store_cache: Callable[[timedelta], None],
    mocks: SimpleNamespace,
) -> None:
    """Een mislukte verbindingspoging wordt onthouden."""
    store_cache(timedelta(hours=1))
    mocks.mesh.ping.return_value = False
    await setup_integration(hass, config_entry)

    result = await async_get_config_entry_diagnostics(hass, config_entry)
    assert result["connection"]["ping_failures"] == 1
    assert dt_util.parse_datetime(result["connection"]["last_ping_failure"])


async def test_battery_level_is_a_separate_entity(
    hass: HomeAssistant, loaded_entry: MockConfigEntry
) -> None:
    """Het batterijniveau van de bewegingssensor is een eigen sensor."""
    entity_id = get_entity_id(hass, "sensor", f"{MOTION}:battery")
    assert hass.states.get(entity_id).state == "unknown"

    push_state(get_device(loaded_entry, MOTION), battery=200)

    assert hass.states.get(entity_id).state == "200"


async def test_battery_level_stays_visible_without_mesh(
    hass: HomeAssistant, loaded_entry: MockConfigEntry
) -> None:
    """Het laatst bekende niveau blijft zichtbaar als het mesh wegvalt."""
    entity_id = get_entity_id(hass, "sensor", f"{MOTION}:battery")
    push_state(get_device(loaded_entry, MOTION), battery=200)

    for device in loaded_entry.runtime_data.devices:
        device.set_available(False)
    await hass.async_block_till_done()

    assert hass.states.get(entity_id).state == "200"


async def test_battery_level_is_restored_after_a_restart(
    hass: HomeAssistant, loaded_entry: MockConfigEntry
) -> None:
    """Na een herstart is het laatste niveau er meteen, tot er een nieuw komt."""
    entity_id = get_entity_id(hass, "sensor", f"{MOTION}:battery")
    assert await hass.config_entries.async_unload(loaded_entry.entry_id)
    mock_restore_cache_with_extra_data(
        hass,
        (
            (
                State(entity_id, "180"),
                {"native_value": 180, "native_unit_of_measurement": None},
            ),
        ),
    )

    await setup_entry(hass, loaded_entry)

    assert hass.states.get(entity_id).state == "180"
    push_state(get_device(loaded_entry, MOTION), battery=190)
    assert hass.states.get(entity_id).state == "190"


async def test_signal_sensors_exist_per_powered_unit_and_are_off(
    hass: HomeAssistant, loaded_entry: MockConfigEntry
) -> None:
    """Elk apparaat op netstroom heeft er twee, ook als het meerdere uitgangen heeft."""
    registry = er.async_get(hass)

    for unit in POWERED_UNITS:
        for key in ("last_seen", "signal_strength"):
            entity_id = registry.async_get_entity_id("sensor", DOMAIN, f"{unit}:{key}")
            assert entity_id is not None, f"{unit}:{key}"
            assert registry.async_get(entity_id).disabled_by is er.RegistryEntryDisabler.INTEGRATION
    assert registry.async_get_entity_id("sensor", DOMAIN, "A0B1C2000005:O:1:last_seen") is None


async def test_signal_sensors_show_the_latest_measurement(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    store_cache: Callable[[timedelta], None],
    mocks: SimpleNamespace,
) -> None:
    """Staan de sensoren aan, dan tonen ze wat we het laatst van het apparaat hoorden."""
    store_cache(timedelta(hours=1))
    config_entry.add_to_hass(hass)
    registry = er.async_get(hass)
    for key in ("last_seen", "signal_strength"):
        registry.async_get_or_create(
            "sensor", DOMAIN, f"{DIMMER}:{key}", config_entry=config_entry
        )
    await setup_entry(hass, config_entry)
    rssi_id = get_entity_id(hass, "sensor", f"{DIMMER}:signal_strength")
    seen_id = get_entity_id(hass, "sensor", f"{DIMMER}:last_seen")
    assert hass.states.get(rssi_id).state == "unknown"

    callback = mocks.bluetooth.register_callback.call_args.args[1]
    callback(service_info(rssi=-80), None)
    callback(service_info(rssi=-61), None)
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(minutes=2))
    await hass.async_block_till_done()

    assert hass.states.get(rssi_id).state == "-61"
    seen = dt_util.parse_datetime(hass.states.get(seen_id).state)
    assert abs(dt_util.utcnow() - seen) < timedelta(minutes=1)
    assert config_entry.runtime_data.signal["A0:B1:C2:00:00:01"].rssi == -61
