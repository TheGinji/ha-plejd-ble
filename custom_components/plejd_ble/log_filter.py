"""Houd de verbindingswaarschuwingen van pyplejd uit de log tijdens een storing."""

from __future__ import annotations

from collections.abc import Callable
import logging
from typing import Final

# pyplejd meldt elke mislukte ronde van verbindingspogingen met twee waarschuwingen
# op deze logger. Is het mesh langere tijd onbereikbaar, dan duurt een ronde 36 tot
# 56 seconden en groeit de log met ongeveer 200 regels per uur.
PYPLEJD_CONNECTION_LOGGER: Final = "pyplejd.ble.connection"
CONNECT_FAILED_PREFIX: Final = "Failed to connect to"


class ConnectFailureFilter(logging.Filter):
    """Zet de waarschuwingen van pyplejd over mislukte verbindingen op debug.

    Dat gebeurt alleen zolang elke site die dit filter gebruikt al een storing
    kent, dus nadat wij zelf hebben gemeld dat er geen verbinding is. Het begin van
    een storing blijft zo zichtbaar, met de oorzaak die pyplejd geeft. Staat
    pyplejd op debug, dan blijven de regels in de log, nu als debug. Staat pyplejd
    niet op debug, dan verdwijnen ze. Een site zonder storing houdt zijn meldingen.
    """

    def __init__(self) -> None:
        """Maak het filter aan, zonder sites."""
        super().__init__()
        self._outage_checks: dict[str, Callable[[], bool]] = {}

    def add_site(self, key: str, in_outage: Callable[[], bool]) -> None:
        """Voeg een site toe en haak het filter aan de pyplejd-logger als dat nog niet is."""
        if not self._outage_checks:
            logging.getLogger(PYPLEJD_CONNECTION_LOGGER).addFilter(self)
        self._outage_checks[key] = in_outage

    def remove_site(self, key: str) -> None:
        """Haal een site weg, en het filter van de logger als er geen meer zijn."""
        self._outage_checks.pop(key, None)
        if not self._outage_checks:
            logging.getLogger(PYPLEJD_CONNECTION_LOGGER).removeFilter(self)

    def filter(self, record: logging.LogRecord) -> bool:
        """Laat de regel door, zet hem op debug of houd hem tegen."""
        if (
            record.levelno != logging.WARNING
            or not isinstance(record.msg, str)
            or not record.msg.startswith(CONNECT_FAILED_PREFIX)
            or not self._outage_checks
            or not all(check() for check in self._outage_checks.values())
        ):
            return True
        if not logging.getLogger(record.name).isEnabledFor(logging.DEBUG):
            return False
        record.levelno = logging.DEBUG
        record.levelname = logging.getLevelName(logging.DEBUG)
        return True


CONNECT_FAILURE_FILTER: Final = ConnectFailureFilter()
