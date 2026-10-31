"""Test dat verwijderen van de integratie de bewaarde sitegegevens opruimt."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.core import HomeAssistant


async def test_removing_the_entry_deletes_the_cached_site_data(
    hass: HomeAssistant, loaded_entry: MockConfigEntry
) -> None:
    """De sitegegevens bevatten sleutels, dus ze blijven niet achter."""
    with patch(
        "homeassistant.helpers.storage.Store.async_remove", new_callable=AsyncMock
    ) as remove:
        assert await hass.config_entries.async_remove(loaded_entry.entry_id)
        await hass.async_block_till_done()

    remove.assert_awaited_once()
