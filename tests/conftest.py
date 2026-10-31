"""Gedeelde fixtures voor de tests van Plejd BLE."""

from __future__ import annotations

from collections.abc import Callable, Generator
import copy
from datetime import timedelta
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

from pyplejd.cloud import PlejdCloudSite
from pyplejd.cloud.site_details import SiteDetails
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from custom_components.plejd_ble.const import CONF_SITE_ID, CONF_SITE_TITLE, DOMAIN

from . import setup_integration

FIXTURES = Path(__file__).parent / "fixtures"
ENTRY_ID = "test-entry-id"
STORE_KEY = f"{DOMAIN}.{ENTRY_ID}"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Laat Home Assistant onze integratie in custom_components vinden."""


@pytest.fixture
def site_data() -> dict[str, Any]:
    """Verzonnen sitegegevens in de vorm van de Plejd-cloud."""
    return json.loads((FIXTURES / "site_details.json").read_text(encoding="utf-8"))


@pytest.fixture
def config_entry() -> MockConfigEntry:
    """Een configuratie-item met verzonnen inloggegevens."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="Voorbeeldstraat 1",
        unique_id="site-1",
        entry_id=ENTRY_ID,
        data={
            "username": "gebruiker@example.com",
            "password": "geheim-wachtwoord",
            CONF_SITE_ID: "site-1",
            CONF_SITE_TITLE: "Voorbeeldstraat 1",
        },
    )


@pytest.fixture
def bluetooth_mock() -> Generator[SimpleNamespace]:
    """Doe alsof er een Bluetooth-adapter is, zonder echte Bluetooth."""
    with (
        patch(
            "homeassistant.components.bluetooth.async_scanner_count", return_value=1
        ) as scanner_count,
        patch(
            "homeassistant.components.bluetooth.async_register_callback",
            return_value=MagicMock(),
        ) as register_callback,
        patch(
            "homeassistant.components.bluetooth.async_discovered_service_info",
            return_value=[],
        ) as discovered,
        patch(
            "homeassistant.components.bluetooth.async_ble_device_from_address",
            return_value=None,
        ) as ble_device,
    ):
        yield SimpleNamespace(
            scanner_count=scanner_count,
            register_callback=register_callback,
            discovered=discovered,
            ble_device=ble_device,
        )


@pytest.fixture
def mesh_mock() -> Generator[SimpleNamespace]:
    """Vervang het Bluetooth-mesh van pyplejd door nepversies."""
    with (
        patch("pyplejd.PlejdManager.ping", AsyncMock(return_value=True)) as ping,
        patch("pyplejd.PlejdManager.broadcast_time", AsyncMock()) as broadcast_time,
        patch("pyplejd.PlejdManager.disconnect", AsyncMock()) as disconnect,
        patch("pyplejd.PlejdManager.close_stale", AsyncMock()) as close_stale,
        patch("pyplejd.PlejdManager.set_blacklist", AsyncMock()) as set_blacklist,
        patch(
            "pyplejd.ble.PlejdMesh.connected",
            new_callable=PropertyMock,
            return_value=True,
        ) as connected,
    ):
        yield SimpleNamespace(
            ping=ping,
            broadcast_time=broadcast_time,
            disconnect=disconnect,
            close_stale=close_stale,
            set_blacklist=set_blacklist,
            connected=connected,
        )


@pytest.fixture
def cloud_mock(site_data: dict[str, Any]) -> Generator[AsyncMock]:
    """Vervang het ophalen van sitegegevens uit de cloud door de testgegevens."""

    async def _get_details(self: PlejdCloudSite) -> None:
        self._details_raw = copy.deepcopy(site_data)
        self.details = SiteDetails(**self._details_raw)

    with patch.object(
        PlejdCloudSite, "get_details", autospec=True, side_effect=_get_details
    ) as mock:
        yield mock


@pytest.fixture
def mocks(
    bluetooth_mock: SimpleNamespace,
    mesh_mock: SimpleNamespace,
    cloud_mock: AsyncMock,
) -> SimpleNamespace:
    """Alle nepversies bij elkaar."""
    return SimpleNamespace(
        bluetooth=bluetooth_mock, mesh=mesh_mock, cloud=cloud_mock
    )


@pytest.fixture
def store_cache(
    hass_storage: dict[str, Any], site_data: dict[str, Any]
) -> Callable[[timedelta], None]:
    """Zet sitegegevens in de lokale cache, met een bepaalde leeftijd."""

    def _store(age: timedelta) -> None:
        fetched_at = dt_util.utcnow() - age
        hass_storage[STORE_KEY] = {
            "version": 1,
            "minor_version": 1,
            "key": STORE_KEY,
            "data": {"fetched_at": fetched_at.isoformat(), "data": site_data},
        }

    return _store


@pytest.fixture
async def loaded_entry(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    store_cache: Callable[[timedelta], None],
    mocks: SimpleNamespace,
) -> MockConfigEntry:
    """Een ingestelde integratie, met een verse cache zodat de cloud niet nodig is."""
    store_cache(timedelta(hours=1))
    await setup_integration(hass, config_entry)
    assert config_entry.state is ConfigEntryState.LOADED
    return config_entry
