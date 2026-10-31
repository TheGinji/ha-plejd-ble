"""Tests voor de configuratiestroom van Plejd BLE."""

from __future__ import annotations

from collections.abc import Generator
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from pyplejd import AuthenticationError, ConnectionError as PlejdConnectionError
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.config_entries import SOURCE_BLUETOOTH, SOURCE_USER
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.plejd_ble.const import CONF_SITE_ID, CONF_SITE_TITLE, DOMAIN

SITE_1 = {"siteId": "site-1", "title": "Voorbeeldstraat 1", "deviceCount": 7}
SITE_2 = {"siteId": "site-2", "title": "Vakantiehuis", "deviceCount": 3}
CREDENTIALS = {"username": "gebruiker@example.com", "password": "geheim-wachtwoord"}


@pytest.fixture
def get_sites() -> Generator[AsyncMock]:
    """Vervang het inloggen bij Plejd door een nepversie met één site."""
    with patch(
        "custom_components.plejd_ble.config_flow.get_sites",
        AsyncMock(return_value=[SITE_1]),
    ) as mock:
        yield mock


@pytest.fixture(autouse=True)
def setup_entry_mock() -> Generator[AsyncMock]:
    """Voorkom dat de integratie echt wordt opgestart."""
    with patch(
        "custom_components.plejd_ble.async_setup_entry", return_value=True
    ) as mock:
        yield mock


async def start_user_flow(hass: HomeAssistant) -> dict:
    """Begin de stroom die de gebruiker zelf start."""
    return await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )


async def test_user_flow_with_one_site(
    hass: HomeAssistant, bluetooth_mock: SimpleNamespace, get_sites: AsyncMock
) -> None:
    """Met één site wordt het item meteen aangemaakt."""
    result = await start_user_flow(hass)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], CREDENTIALS
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Voorbeeldstraat 1"
    assert result["data"] == {
        **CREDENTIALS,
        CONF_SITE_ID: "site-1",
        CONF_SITE_TITLE: "Voorbeeldstraat 1",
    }
    assert result["result"].unique_id == "site-1"
    get_sites.assert_awaited_once_with(
        username=CREDENTIALS["username"], password=CREDENTIALS["password"]
    )


async def test_user_flow_with_several_sites(
    hass: HomeAssistant, bluetooth_mock: SimpleNamespace, get_sites: AsyncMock
) -> None:
    """Met meer sites mag de gebruiker er één kiezen."""
    get_sites.return_value = [SITE_1, SITE_2]
    result = await start_user_flow(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], CREDENTIALS
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "site"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_SITE_ID: "site-2"}
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Vakantiehuis"
    assert result["data"][CONF_SITE_ID] == "site-2"


@pytest.mark.parametrize(
    ("exception", "error"),
    [
        (AuthenticationError, "invalid_auth"),
        (PlejdConnectionError, "cannot_connect"),
        (RuntimeError, "unknown"),
    ],
)
async def test_user_flow_errors_can_be_recovered(
    hass: HomeAssistant,
    bluetooth_mock: SimpleNamespace,
    get_sites: AsyncMock,
    exception: type[Exception],
    error: str,
) -> None:
    """Na een fout kan de gebruiker het opnieuw proberen."""
    get_sites.side_effect = exception
    result = await start_user_flow(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], CREDENTIALS
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": error}

    get_sites.side_effect = None
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], CREDENTIALS
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY


async def test_user_flow_without_sites(
    hass: HomeAssistant, bluetooth_mock: SimpleNamespace, get_sites: AsyncMock
) -> None:
    """Een account zonder sites stopt de stroom."""
    get_sites.return_value = []
    result = await start_user_flow(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], CREDENTIALS
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "no_sites"


async def test_user_flow_without_bluetooth(
    hass: HomeAssistant, bluetooth_mock: SimpleNamespace, get_sites: AsyncMock
) -> None:
    """Zonder Bluetooth-adapter of proxy kan Plejd niet worden ingesteld."""
    bluetooth_mock.scanner_count.return_value = 0
    result = await start_user_flow(hass)
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "bluetooth_not_available"


async def test_site_can_only_be_added_once(
    hass: HomeAssistant,
    bluetooth_mock: SimpleNamespace,
    get_sites: AsyncMock,
    config_entry: MockConfigEntry,
) -> None:
    """Dezelfde site tweemaal toevoegen is niet mogelijk."""
    config_entry.add_to_hass(hass)
    result = await start_user_flow(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], CREDENTIALS
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_bluetooth_discovery_starts_user_step(
    hass: HomeAssistant, bluetooth_mock: SimpleNamespace, get_sites: AsyncMock
) -> None:
    """Een gevonden Plejd-apparaat leidt naar het inlogscherm, maar één keer."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_BLUETOOTH}, data=MagicMock()
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    second = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_BLUETOOTH}, data=MagicMock()
    )
    assert second["type"] is FlowResultType.ABORT
    assert second["reason"] == "already_in_progress"


async def test_bluetooth_discovery_ignored_when_configured(
    hass: HomeAssistant,
    bluetooth_mock: SimpleNamespace,
    config_entry: MockConfigEntry,
) -> None:
    """Als er al een site is, doen we niets met een ontdekking."""
    config_entry.add_to_hass(hass)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_BLUETOOTH}, data=MagicMock()
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_reauth_flow(
    hass: HomeAssistant,
    bluetooth_mock: SimpleNamespace,
    get_sites: AsyncMock,
    config_entry: MockConfigEntry,
) -> None:
    """Nieuwe inloggegevens worden opgeslagen na opnieuw inloggen."""
    config_entry.add_to_hass(hass)
    result = await config_entry.start_reauth_flow(hass)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reauth_confirm"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"username": "nieuw@example.com", "password": "nieuw-wachtwoord"},
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert config_entry.data["username"] == "nieuw@example.com"
    assert config_entry.data["password"] == "nieuw-wachtwoord"
    assert config_entry.data[CONF_SITE_ID] == "site-1"


async def test_reauth_flow_errors(
    hass: HomeAssistant,
    bluetooth_mock: SimpleNamespace,
    get_sites: AsyncMock,
    config_entry: MockConfigEntry,
) -> None:
    """Een verkeerd wachtwoord of een andere site geeft een foutmelding."""
    config_entry.add_to_hass(hass)
    result = await config_entry.start_reauth_flow(hass)

    get_sites.side_effect = AuthenticationError
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], CREDENTIALS
    )
    assert result["errors"] == {"base": "invalid_auth"}

    get_sites.side_effect = None
    get_sites.return_value = [SITE_2]
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], CREDENTIALS
    )
    assert result["errors"] == {"base": "site_not_found"}


async def test_reconfigure_flow(
    hass: HomeAssistant,
    bluetooth_mock: SimpleNamespace,
    get_sites: AsyncMock,
    config_entry: MockConfigEntry,
) -> None:
    """De inloggegevens kunnen achteraf worden gewijzigd."""
    config_entry.add_to_hass(hass)
    result = await config_entry.start_reconfigure_flow(hass)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reconfigure"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"username": "ander@example.com", "password": "ander-wachtwoord"},
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert config_entry.data["username"] == "ander@example.com"
