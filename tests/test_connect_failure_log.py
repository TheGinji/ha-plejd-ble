"""Tests voor het filter dat de verbindingswaarschuwingen van pyplejd tijdens een storing op debug zet."""

from __future__ import annotations

from collections.abc import Callable, Generator
from datetime import timedelta
import logging
from types import SimpleNamespace

import pytest
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)

from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from custom_components.plejd_ble.log_filter import (
    CONNECT_FAILURE_FILTER,
    PYPLEJD_CONNECTION_LOGGER,
    ConnectFailureFilter,
)

from . import setup_integration
from .conftest import ENTRY_ID

PYPLEJD = logging.getLogger(PYPLEJD_CONNECTION_LOGGER)


@pytest.fixture(autouse=True)
def clean_logger() -> Generator[None]:
    """Begin en eindig zonder filter op de logger van pyplejd."""
    CONNECT_FAILURE_FILTER.remove_site(ENTRY_ID)
    PYPLEJD.removeFilter(CONNECT_FAILURE_FILTER)
    yield
    CONNECT_FAILURE_FILTER.remove_site(ENTRY_ID)
    PYPLEJD.removeFilter(CONNECT_FAILURE_FILTER)


@pytest.fixture
def own_filter() -> Generator[ConnectFailureFilter]:
    """Een eigen filter, los van dat van de integratie, dat achteraf weer wordt weggehaald."""
    log_filter = ConnectFailureFilter()
    yield log_filter
    PYPLEJD.removeFilter(log_filter)


def pyplejd_records(caplog: pytest.LogCaptureFixture) -> list[logging.LogRecord]:
    """Geef de regels die van de logger van pyplejd zijn gekomen."""
    return [r for r in caplog.records if r.name == PYPLEJD_CONNECTION_LOGGER]


def failed_round() -> None:
    """Meld een mislukte ronde, zoals pyplejd dat doet."""
    PYPLEJD.warning("Failed to connect to %s: %s", "apparaat", "geen verbinding")
    PYPLEJD.warning("Failed to connect to plejd mesh - %s", ["apparaat"])


async def advance(hass: HomeAssistant, seconds: int) -> None:
    """Laat de tijd vooruitlopen en wacht tot alles is afgehandeld."""
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=seconds))
    await hass.async_block_till_done()


def test_failures_are_kept_without_an_outage(
    own_filter: ConnectFailureFilter, caplog: pytest.LogCaptureFixture
) -> None:
    """Zonder storing blijven de waarschuwingen van pyplejd zoals ze zijn."""
    caplog.set_level(logging.WARNING, logger=PYPLEJD_CONNECTION_LOGGER)
    own_filter.add_site("site", lambda: False)

    failed_round()

    records = pyplejd_records(caplog)
    assert len(records) == 2
    assert {record.levelno for record in records} == {logging.WARNING}


def test_failures_are_hidden_during_an_outage(
    own_filter: ConnectFailureFilter, caplog: pytest.LogCaptureFixture
) -> None:
    """Tijdens een storing verdwijnen ze, zolang pyplejd niet op debug staat."""
    caplog.set_level(logging.WARNING, logger=PYPLEJD_CONNECTION_LOGGER)
    own_filter.add_site("site", lambda: True)

    failed_round()

    assert pyplejd_records(caplog) == []


def test_failures_become_debug_when_pyplejd_logs_debug(
    own_filter: ConnectFailureFilter, caplog: pytest.LogCaptureFixture
) -> None:
    """Staat pyplejd op debug, dan blijven ze in de log, nu als debug."""
    caplog.set_level(logging.DEBUG, logger=PYPLEJD_CONNECTION_LOGGER)
    own_filter.add_site("site", lambda: True)

    failed_round()

    records = pyplejd_records(caplog)
    assert len(records) == 2
    assert {record.levelno for record in records} == {logging.DEBUG}
    assert {record.levelname for record in records} == {"DEBUG"}
    assert "Failed to connect to plejd mesh" in records[1].getMessage()


def test_other_messages_are_left_alone(
    own_filter: ConnectFailureFilter, caplog: pytest.LogCaptureFixture
) -> None:
    """Andere regels van pyplejd, ook tijdens een storing, blijven zoals ze zijn."""
    caplog.set_level(logging.WARNING, logger=PYPLEJD_CONNECTION_LOGGER)
    own_filter.add_site("site", lambda: True)

    PYPLEJD.warning("Iets anders is misgegaan")
    PYPLEJD.error("Failed to connect to %s", "apparaat")

    records = pyplejd_records(caplog)
    assert [record.levelno for record in records] == [logging.WARNING, logging.ERROR]


def test_hidden_only_when_every_site_has_an_outage(
    own_filter: ConnectFailureFilter, caplog: pytest.LogCaptureFixture
) -> None:
    """Met twee sites houdt een site zonder storing zijn waarschuwingen."""
    caplog.set_level(logging.WARNING, logger=PYPLEJD_CONNECTION_LOGGER)
    healthy = {"outage": False}
    own_filter.add_site("een", lambda: True)
    own_filter.add_site("twee", lambda: healthy["outage"])

    failed_round()
    assert len(pyplejd_records(caplog)) == 2

    healthy["outage"] = True
    caplog.clear()
    failed_round()
    assert pyplejd_records(caplog) == []

    own_filter.remove_site("twee")
    own_filter.add_site("twee", lambda: False)
    failed_round()
    assert len(pyplejd_records(caplog)) == 2


def test_filter_is_on_the_logger_only_while_there_are_sites(
    own_filter: ConnectFailureFilter,
) -> None:
    """Het filter hangt aan de logger van pyplejd zolang er een site is."""
    assert own_filter not in PYPLEJD.filters

    own_filter.add_site("een", lambda: False)
    own_filter.add_site("twee", lambda: False)
    assert own_filter in PYPLEJD.filters

    own_filter.remove_site("een")
    assert own_filter in PYPLEJD.filters

    own_filter.remove_site("twee")
    own_filter.remove_site("twee")
    assert own_filter not in PYPLEJD.filters


async def test_warnings_stop_after_the_integration_reports_the_outage(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    store_cache: Callable[[timedelta], None],
    mocks: SimpleNamespace,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Na onze eigen melding zijn de waarschuwingen van pyplejd weg, tot de verbinding terug is."""
    caplog.set_level(logging.WARNING, logger=PYPLEJD_CONNECTION_LOGGER)
    caplog.set_level(logging.INFO, logger="custom_components.plejd_ble.site")
    store_cache(timedelta(hours=1))
    mocks.mesh.ping.return_value = False
    await setup_integration(hass, config_entry)

    failed_round()
    assert len(pyplejd_records(caplog)) == 2

    await advance(hass, 11)
    assert caplog.text.count("Geen verbinding met het Plejd-mesh") == 1
    caplog.clear()
    failed_round()
    assert pyplejd_records(caplog) == []

    await advance(hass, 45)
    mocks.mesh.ping.return_value = True
    await advance(hass, 100)
    assert "De verbinding met het Plejd-mesh is hersteld" in caplog.text

    caplog.clear()
    failed_round()
    assert len(pyplejd_records(caplog)) == 2


async def test_filter_is_removed_when_the_integration_unloads(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    store_cache: Callable[[timedelta], None],
    mocks: SimpleNamespace,
) -> None:
    """Haalt de integratie zijn site weg, dan laat het filter de logger los."""
    store_cache(timedelta(hours=1))
    await setup_integration(hass, config_entry)
    assert CONNECT_FAILURE_FILTER in PYPLEJD.filters

    assert await hass.config_entries.async_unload(config_entry.entry_id)

    assert CONNECT_FAILURE_FILTER not in PYPLEJD.filters
