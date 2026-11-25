"""Tests voor het apparaat waarlangs we verbonden zijn: het zendt niets uit.

Zolang de verbinding openstaat hoort Home Assistant dat apparaat niet meer. Zijn
signaal en laatst-gezien blijven dan op het begin van de verbinding staan. Wat we
wel weten: het antwoordt op onze keep-alive.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import patch

from freezegun.api import FrozenDateTimeFactory
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util

from custom_components.plejd_ble.const import DOMAIN
from custom_components.plejd_ble.diagnostics import async_get_config_entry_diagnostics
from custom_components.plejd_ble.signal_quality import signal_label
from custom_components.plejd_ble.site import PlejdSite

from . import CEILING_1, DIMMER, get_device, get_entity, get_entity_id, setup_entry

GREEN = "\U0001F7E2"
WHITE = "⚪"
LINK = "\U0001F517"
DIMMER_ADDRESS = "A0:B1:C2:00:00:01"
CEILING_ADDRESS = "A0:B1:C2:00:00:02"


def service_info(address: str, rssi: int) -> SimpleNamespace:
    """Maak een verzonnen Bluetooth-melding van een Plejd-apparaat."""
    return SimpleNamespace(device=SimpleNamespace(address=address, name="Plejd"), rssi=rssi)


def connect_through(entry: MockConfigEntry, identifier: str) -> str:
    """Doe alsof we verbonden zijn via dit apparaat en geef zijn adres terug."""
    address = get_device(entry, identifier).BLEaddress
    entry.runtime_data.manager.mesh._gateway_node = SimpleNamespace(BLEaddress=address)
    return address


def test_signal_label_always_marks_the_connected_unit() -> None:
    """Het verbonden apparaat heeft altijd een schakel, met of zonder meting."""
    assert signal_label(None, connected=True) == f"{LINK} – dBm"
    assert signal_label(-60, connected=True) == f"{LINK} {GREEN} -60 dBm"
    assert signal_label(None) == f"{WHITE} – dBm"
    assert signal_label(-60) == f"{GREEN} -60 dBm"


async def test_options_mark_the_connected_unit(
    hass: HomeAssistant, loaded_entry: MockConfigEntry, mocks: SimpleNamespace
) -> None:
    """Het verbonden apparaat krijgt een schakel, de andere zonder meting een witte stip."""
    address = connect_through(loaded_entry, DIMMER)

    result = await hass.config_entries.options.async_init(loaded_entry.entry_id)
    selector = next(iter(result["data_schema"].schema.values()))
    labels = {option["value"]: option["label"] for option in selector.config["options"]}

    assert labels[address].startswith(f"{LINK} ")
    assert labels["A0B1C2000002"].startswith(f"{WHITE} ")


async def test_options_show_a_fresh_measurement_of_the_connected_unit_too(
    hass: HomeAssistant, loaded_entry: MockConfigEntry, mocks: SimpleNamespace
) -> None:
    """Vlak na het verbinden is er nog een meting: de schakel staat er dan ook bij."""
    address = connect_through(loaded_entry, DIMMER)
    callback = mocks.bluetooth.register_callback.call_args.args[1]
    callback(service_info(DIMMER_ADDRESS, -55), None)

    result = await hass.config_entries.options.async_init(loaded_entry.entry_id)
    selector = next(iter(result["data_schema"].schema.values()))
    labels = {option["value"]: option["label"] for option in selector.config["options"]}

    assert labels[address].startswith(f"{LINK} {GREEN} -55 dBm")


async def test_a_ping_is_recorded_for_the_connected_unit(
    hass: HomeAssistant,
    loaded_entry: MockConfigEntry,
    mocks: SimpleNamespace,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Een geslaagde keep-alive telt als teken van leven van het verbonden apparaat."""
    site = loaded_entry.runtime_data

    await site._async_ping()
    assert site.link_heard == {}

    address = connect_through(loaded_entry, DIMMER)
    freezer.tick(timedelta(minutes=3))
    await site._async_ping()

    assert site.link_heard == {address: dt_util.utcnow()}


async def test_a_failed_ping_is_not_recorded(
    hass: HomeAssistant, loaded_entry: MockConfigEntry, mocks: SimpleNamespace
) -> None:
    """Een keep-alive zonder antwoord bewijst niets."""
    site = loaded_entry.runtime_data
    connect_through(loaded_entry, DIMMER)
    mocks.mesh.ping.return_value = False

    with patch.object(PlejdSite, "_schedule_reconnect"):
        await site._async_ping()

    assert site.link_heard == {}


async def test_sensors_of_the_connected_unit_do_not_go_stale(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    store_cache: Callable[[timedelta], None],
    mocks: SimpleNamespace,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Na een kwartier is het signaal van het verbonden apparaat onbekend, laatst gezien actueel."""
    store_cache(timedelta(hours=1))
    config_entry.add_to_hass(hass)
    registry = er.async_get(hass)
    for identifier in (DIMMER, CEILING_1):
        for key in ("last_seen", "signal_strength"):
            registry.async_get_or_create(
                "sensor", DOMAIN, f"{identifier}:{key}", config_entry=config_entry
            )
    await setup_entry(hass, config_entry)
    site = config_entry.runtime_data
    connect_through(config_entry, DIMMER)
    heard_at = dt_util.utcnow()

    async def states() -> dict[str, str]:
        result = {}
        for identifier in (DIMMER, CEILING_1):
            for key in ("last_seen", "signal_strength"):
                entity_id = get_entity_id(hass, "sensor", f"{identifier}:{key}")
                await get_entity(hass, entity_id).async_update_ha_state()
                result[f"{identifier}:{key}"] = hass.states.get(entity_id).state
        return result

    assert (await states())[f"{DIMMER}:signal_strength"] == "unknown"

    callback = mocks.bluetooth.register_callback.call_args.args[1]
    callback(service_info(DIMMER_ADDRESS, -60), None)
    callback(service_info(CEILING_ADDRESS, -62), None)
    assert (await states())[f"{DIMMER}:signal_strength"] == "-60"

    freezer.tick(timedelta(minutes=20))
    await site._async_ping()
    now = await states()

    assert now[f"{DIMMER}:signal_strength"] == "unknown"
    last_seen = dt_util.parse_datetime(now[f"{DIMMER}:last_seen"])
    assert abs(last_seen - dt_util.utcnow()) < timedelta(seconds=2)
    # Een apparaat dat niet het verbonden apparaat is, houdt zijn laatste meting.
    assert now[f"{CEILING_1}:signal_strength"] == "-62"
    ceiling_seen = dt_util.parse_datetime(now[f"{CEILING_1}:last_seen"])
    assert abs(ceiling_seen - heard_at) < timedelta(seconds=2)


async def test_diagnostics_show_the_connected_unit_and_when_it_was_heard(
    hass: HomeAssistant,
    loaded_entry: MockConfigEntry,
    mocks: SimpleNamespace,
) -> None:
    """In de diagnostiek staat welk apparaat de verbinding vormt en wanneer het antwoordde."""
    result = await async_get_config_entry_diagnostics(hass, loaded_entry)
    assert not any(device["connected_unit"] for device in result["devices"])
    assert all(device["last_heard"] is None for device in result["devices"])

    connect_through(loaded_entry, DIMMER)
    await loaded_entry.runtime_data._async_ping()
    result = await async_get_config_entry_diagnostics(hass, loaded_entry)

    connected = [device for device in result["devices"] if device["connected_unit"]]
    assert len(connected) == 1
    assert connected[0]["last_heard"] is not None
    assert connected[0]["last_seen"] is None
