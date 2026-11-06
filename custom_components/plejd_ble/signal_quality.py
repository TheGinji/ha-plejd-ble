"""Hoe goed is het Bluetooth-signaal van een apparaat?"""

from __future__ import annotations

from datetime import timedelta

# Hoeveel metingen we meenemen voor het gemiddelde: een enkele meting schommelt snel.
RSSI_SAMPLES = 10

# Een meting die ouder is dan dit, tonen we niet meer als het huidige signaal.
SIGNAL_MAX_AGE = timedelta(minutes=15)

# Zo vaak vragen we Home Assistant om het volgende bericht van elk apparaat door te geven.
SIGNAL_REFRESH_INTERVAL = timedelta(minutes=1)

# Vuistregels voor Bluetooth in dBm, geen waarden van Plejd.
GOOD_RSSI = -65
FAIR_RSSI = -80

_GREEN = "\U0001F7E2"
_ORANGE = "\U0001F7E0"
_RED = "\U0001F534"
_WHITE = "\u26AA"


def signal_label(rssi: int | None) -> str:
    """Geef een kort label: een gekleurde stip en de signaalsterkte in dBm."""
    if rssi is None:
        return f"{_WHITE} \u2013 dBm"
    if rssi >= GOOD_RSSI:
        dot = _GREEN
    elif rssi >= FAIR_RSSI:
        dot = _ORANGE
    else:
        dot = _RED
    return f"{dot} {rssi} dBm"
