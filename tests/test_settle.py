"""Tests voor het tweede verbinden met hetzelfde apparaat."""

from __future__ import annotations

from collections.abc import Generator
import json
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.core import HomeAssistant

from custom_components.plejd_ble.diagnostics import async_get_config_entry_diagnostics


@pytest.fixture(autouse=True)
def settle_on() -> Generator[None]:
    """Zet de tweede verbinding aan, ook als hij in de code tijdelijk uit staat."""
    with patch("custom_components.plejd_ble.site.SETTLE_CONNECTION", True):
        yield


def pick_gateway(entry: MockConfigEntry, index: int = 0) -> tuple[Any, str]:
    """Doe alsof we verbonden zijn via het apparaat met dit volgnummer."""
    site = entry.runtime_data
    address = sorted(site.manager.hardware)[index]
    site.manager.mesh._gateway_node = SimpleNamespace(BLEaddress=address)
    return site, address


async def test_first_connection_to_a_unit_is_made_a_second_time(
    hass: HomeAssistant, loaded_entry: MockConfigEntry, mocks: SimpleNamespace
) -> None:
    """De eerste verbinding wordt meteen herhaald, met alleen dat ene apparaat."""
    site, address = pick_gateway(loaded_entry)
    seen: list[dict[str, bool]] = []

    async def fake_ping(*_args: Any, **_kwargs: Any) -> bool:
        seen.append({a: hw.blacklisted for a, hw in site.manager.hardware.items()})
        return True

    mocks.mesh.ping.side_effect = fake_ping
    mocks.mesh.disconnect.reset_mock()

    await site._async_ping()

    assert mocks.mesh.disconnect.await_count == 1
    assert len(seen) == 2
    assert not any(seen[0].values())
    assert seen[1][address] is False
    assert all(blocked for other, blocked in seen[1].items() if other != address)
    assert not any(hw.blacklisted for hw in site.manager.hardware.values())
    assert site.settled_units == 1
    assert site.last_settle is not None


async def test_the_same_unit_is_only_settled_once(
    hass: HomeAssistant, loaded_entry: MockConfigEntry, mocks: SimpleNamespace
) -> None:
    """Bij de volgende controles blijft de verbinding gewoon staan."""
    site, _address = pick_gateway(loaded_entry)
    mocks.mesh.disconnect.reset_mock()

    await site._async_ping()
    await site._async_ping()

    assert mocks.mesh.disconnect.await_count == 1


async def test_a_new_unit_is_settled_when_the_connection_moves(
    hass: HomeAssistant, loaded_entry: MockConfigEntry, mocks: SimpleNamespace
) -> None:
    """Wisselt de verbinding naar een ander apparaat, dan geldt dat ook daar."""
    site, _first = pick_gateway(loaded_entry, 0)
    mocks.mesh.disconnect.reset_mock()
    await site._async_ping()

    pick_gateway(loaded_entry, 1)
    await site._async_ping()

    assert mocks.mesh.disconnect.await_count == 2
    assert site.settled_units == 2


async def test_blocked_units_stay_blocked(
    hass: HomeAssistant, loaded_entry: MockConfigEntry, mocks: SimpleNamespace
) -> None:
    """Een apparaat dat de gebruiker heeft uitgezet, blijft uit na het tweede verbinden."""
    site, address = pick_gateway(loaded_entry, 0)
    blocked = sorted(site.manager.hardware)[1]
    site.manager.hardware[blocked].blacklisted = True

    await site._async_ping()

    assert site.manager.hardware[blocked].blacklisted is True
    assert site.manager.hardware[address].blacklisted is False


async def test_failed_second_connection_is_retried(
    hass: HomeAssistant, loaded_entry: MockConfigEntry, mocks: SimpleNamespace
) -> None:
    """Lukt het tweede verbinden niet, dan staat alles weer terug en volgt een nieuwe poging."""
    site, _address = pick_gateway(loaded_entry)
    mocks.mesh.ping.side_effect = [True, False]

    await site._async_ping()

    assert not any(hw.blacklisted for hw in site.manager.hardware.values())
    assert site.ping_failures == 1
    assert site._cancel_reconnect is not None
    site._cancel_reconnect()
    site._cancel_reconnect = None


async def test_settle_is_skipped_when_switched_off(
    hass: HomeAssistant, loaded_entry: MockConfigEntry, mocks: SimpleNamespace
) -> None:
    """Staat de tweede verbinding uit, dan blijft de eerste verbinding gewoon staan."""
    site, _address = pick_gateway(loaded_entry)
    mocks.mesh.disconnect.reset_mock()

    with patch("custom_components.plejd_ble.site.SETTLE_CONNECTION", False):
        await site._async_ping()
        result = await async_get_config_entry_diagnostics(hass, loaded_entry)

    assert mocks.mesh.disconnect.await_count == 0
    assert site.settled_units == 0
    assert result["settle"]["enabled"] is False


async def test_diagnostics_count_settled_units_without_addresses(
    hass: HomeAssistant, loaded_entry: MockConfigEntry
) -> None:
    """De diagnostiek toont alleen hoeveel apparaten het betreft."""
    site, address = pick_gateway(loaded_entry)
    await site._async_ping()

    result = await async_get_config_entry_diagnostics(hass, loaded_entry)

    assert result["settle"]["enabled"] is True
    assert result["settle"]["units"] == 1
    assert result["settle"]["last"] is not None
    assert address not in json.dumps(result)
