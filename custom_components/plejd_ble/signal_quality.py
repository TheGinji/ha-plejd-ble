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
_WHITE = "⚪"
_LINK = "\U0001F517"


def signal_label(rssi: int | None, connected: bool = False) -> str:
    """Geef een kort label: een gekleurde stip en de signaalsterkte in dBm.

    Het apparaat waarlangs we verbonden zijn, zendt niets uit zolang de verbinding
    openstaat. Dat apparaat krijgt altijd een schakel voorop. Heeft het geen
    recente meting, dan staat er een streepje in plaats van een witte stip, want
    het ontbreken van een meting zegt hier niets.
    """
    if rssi is None:
        return f"{_LINK} – dBm" if connected else f"{_WHITE} – dBm"
    if rssi >= GOOD_RSSI:
        dot = _GREEN
    elif rssi >= FAIR_RSSI:
        dot = _ORANGE
    else:
        dot = _RED
    label = f"{dot} {rssi} dBm"
    return f"{_LINK} {label}" if connected else label
