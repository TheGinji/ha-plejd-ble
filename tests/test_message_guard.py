"""Tests voor het opvangen van fouten in berichten uit het mesh."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from pyplejd.ble.lastdata import LastData
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.core import HomeAssistant

from custom_components.plejd_ble.diagnostics import async_get_config_entry_diagnostics


def empty_state_message() -> LastData:
    """Een bericht aan alle apparaten met een leeg stuk gegevens, zoals het mesh er één stuurde."""
    return LastData(address=0, command=LastData.CMD_GROUP_OUTPUT_STATE, payload=[])


async def test_message_with_empty_content_is_caught_and_counted(
    hass: HomeAssistant,
    loaded_entry: MockConfigEntry,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Het bericht dat pyplejd liet crashen wordt opgevangen, geteld en één keer gemeld."""
    site = loaded_entry.runtime_data

    await site.manager.lastdata_callback(empty_state_message())
    await site.manager.lastdata_callback(empty_state_message())

    assert site.message_errors >= 2
    assert caplog.text.count("kon niet worden verwerkt") == 1
    assert "commando 0x0097, 0 bytes, IndexError" in site.last_message_error_info


async def test_one_failing_device_does_not_block_the_others(
    hass: HomeAssistant, loaded_entry: MockConfigEntry
) -> None:
    """Faalt een apparaat, dan krijgen de apparaten daarna het bericht nog steeds."""
    site = loaded_entry.runtime_data
    good_handler = AsyncMock()
    bad = SimpleNamespace(
        address=0, rxAddress=0, parse_lastdata=AsyncMock(side_effect=IndexError("kapot"))
    )
    good = SimpleNamespace(address=0, rxAddress=0, parse_lastdata=good_handler)
    site.manager.devices.extend([bad, good])
    try:
        site._guard_message_handlers()
        await site.manager.lastdata_callback(empty_state_message())
    finally:
        site.manager.devices.remove(bad)
        site.manager.devices.remove(good)

    good_handler.assert_awaited_once()


async def test_guard_is_applied_once_and_skips_devices_without_a_handler(
    hass: HomeAssistant, loaded_entry: MockConfigEntry
) -> None:
    """Dubbel inpakken gebeurt niet, en een apparaat zonder verwerking blijft ongemoeid."""
    site = loaded_entry.runtime_data
    fake = SimpleNamespace(address=1, rxAddress=1, parse_lastdata=AsyncMock())
    without_handler = SimpleNamespace(address=2, rxAddress=2)
    site.manager.devices.extend([fake, without_handler])
    try:
        site._guard_message_handlers()
        first = fake.parse_lastdata
        site._guard_message_handlers()

        assert fake.parse_lastdata is first
        assert not hasattr(without_handler, "parse_lastdata")
    finally:
        site.manager.devices.remove(fake)
        site.manager.devices.remove(without_handler)


async def test_diagnostics_show_message_errors_without_addresses(
    hass: HomeAssistant, loaded_entry: MockConfigEntry
) -> None:
    """De diagnostiek toont het aantal en het soort fout, en geen adressen."""
    site = loaded_entry.runtime_data
    before = await async_get_config_entry_diagnostics(hass, loaded_entry)
    assert before["messages"] == {
        "errors": 0,
        "last_error": None,
        "last_error_info": None,
    }

    await site.manager.lastdata_callback(empty_state_message())

    after = (await async_get_config_entry_diagnostics(hass, loaded_entry))["messages"]
    assert after["errors"] >= 1
    assert after["last_error"] is not None
    assert after["last_error_info"].startswith("commando 0x0097")
