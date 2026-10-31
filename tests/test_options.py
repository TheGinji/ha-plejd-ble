"""Tests voor de opties: welke apparaten mogen als Bluetooth-ingang dienen?"""

from __future__ import annotations

from collections.abc import Callable
from datetime import timedelta
from types import SimpleNamespace

from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from . import setup_integration

# De apparaten op netstroom in tests/fixtures/site_details.json.
POWERED = ["A0B1C2000001", "A0B1C2000002", "A0B1C2000003", "A0B1C2000004", "A0B1C2000005"]


async def test_gateway_candidates_are_the_powered_devices(
    hass: HomeAssistant, loaded_entry: MockConfigEntry
) -> None:
    """Alleen apparaten op netstroom komen in de lijst, elk één keer."""
    candidates = loaded_entry.runtime_data.gateway_candidates()

    assert list(candidates) == POWERED
    assert candidates["A0B1C2000001"] == "Zithoek (Woonkamer)"
    assert candidates["A0B1C2000005"] == "Wandlamp (Woonkamer)"


async def test_options_flow_saves_the_blocked_devices(
    hass: HomeAssistant, loaded_entry: MockConfigEntry, mocks: SimpleNamespace
) -> None:
    """Wat niet is aangevinkt wordt geblokkeerd en direct toegepast."""
    result = await hass.config_entries.options.async_init(loaded_entry.entry_id)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"allowed_devices": POWERED[:2]}
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert loaded_entry.options == {"blocked_devices": POWERED[2:]}
    mocks.mesh.set_blacklist.assert_awaited_once_with(POWERED[2:])


async def test_options_flow_needs_at_least_one_device(
    hass: HomeAssistant, loaded_entry: MockConfigEntry
) -> None:
    """Zonder enige toegestane ingang zou er nooit verbinding komen."""
    result = await hass.config_entries.options.async_init(loaded_entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"allowed_devices": []}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "no_gateway"}


async def test_options_flow_remembers_earlier_choices(
    hass: HomeAssistant, loaded_entry: MockConfigEntry
) -> None:
    """Een eerdere keuze staat al aangevinkt als je de opties opnieuw opent."""
    hass.config_entries.async_update_entry(
        loaded_entry, options={"blocked_devices": POWERED[3:]}
    )
    await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(loaded_entry.entry_id)
    schema = result["data_schema"].schema
    default = next(iter(schema)).default()

    assert default == POWERED[:3]


async def test_options_flow_needs_a_running_integration(
    hass: HomeAssistant, config_entry: MockConfigEntry
) -> None:
    """Zolang de integratie niet draait, is er niets te kiezen."""
    config_entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(config_entry.entry_id)

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "not_loaded"


async def test_blocked_devices_are_used_at_startup(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    store_cache: Callable[[timedelta], None],
    mocks: SimpleNamespace,
) -> None:
    """Geblokkeerde apparaten worden vanaf het begin niet als ingang gebruikt."""
    store_cache(timedelta(hours=1))
    config_entry.add_to_hass(hass)
    hass.config_entries.async_update_entry(
        config_entry, options={"blocked_devices": ["A0B1C2000001"]}
    )
    await setup_integration(hass, config_entry)

    assert config_entry.runtime_data.manager.blacklist == {"A0B1C2000001"}
