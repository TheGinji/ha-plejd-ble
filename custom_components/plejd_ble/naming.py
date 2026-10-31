"""Namen voor Plejd-apparaten, zonder lege namen en zonder dubbelen per kamer."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

# Productnamen zoals Plejd ze zelf gebruikt, op basis van Plejds eigen
# productbladen en catalogus. Bevestigd in het Engels: WPH-01, WMS-01, LED-75,
# DIM-01, DIM-02, TRM-01, DWN, OUT-01, GWY-01, EXT-01, RTR-01, SPR-01 en LST-01.
# Letterlijk vertaald uit de Duitse of Franse catalogus: REL-01, REL-02, CTR-01,
# DAL-01, JAL-01, VRI-03 en LED-10. Een model dat hier niet staat, houdt zijn
# modelnummer. De sleutel is de productfamilie, dus WPH-01-LC valt onder WPH-01.
PRODUCT_NAMES = {
    "CTR-01": "Dimmer 1-10 V",
    "DAL-01": "DALI broadcast controller",
    "DIM-01": "Dimmer LED",
    "DIM-02": "2-channel dimmer LED",
    "DWN-01": "Downlight",
    "DWN-02": "Downlight",
    "EXT-01": "Extender",
    "GWY-01": "Gateway",
    "JAL-01": "Blind controller",
    "LED-10": "LED driver 10 W",
    "LED-75": "LED driver 75 W",
    "LST-01": "LED strip",
    "OUT-01": "Outdoor luminaire",
    "REL-01": "Relay 16 A",
    "REL-02": "2-channel relay",
    "RTR-01": "Rotary adapter",
    "SPR-01": "Smart plug on/off",
    "TRM-01": "Thermostat",
    "VRI-03": "Rotary dimmer",
    "WMS-01": "Wireless motion sensor",
    "WPH-01": "Wireless push button",
}


def product_name(hardware: str) -> str:
    """Geef de productnaam bij een model, of het modelnummer zelf als die onbekend is."""
    model = hardware.strip()
    family = "-".join(model.split("-")[:2])
    return PRODUCT_NAMES.get(family, model)


@dataclass(frozen=True)
class NameSource:
    """Gegevens uit de Plejd-cloud waarmee we een apparaatnaam bepalen."""

    identifier: str
    title: str
    room: str
    hardware: str


def _first_choice(source: NameSource) -> str:
    """Geef de titel uit de cloud, of anders de productnaam of het model."""
    return source.title.strip() or product_name(source.hardware) or "Plejd"


def build_names(sources: list[NameSource]) -> dict[str, str]:
    """Bepaal per apparaat een naam die duidelijk en voorspelbaar is.

    De kamer zetten we bewust niet in de naam: Home Assistant zet de kamer zelf
    voor de entiteit-ID, zodat "Plafondlicht" in twee slaapkamers
    "slaapkamer_1_plafondlicht" en "slaapkamer_2_plafondlicht" wordt. Alleen
    apparaten met dezelfde naam in dezelfde kamer krijgen een volgnummer.
    """
    by_id = {source.identifier: source for source in sources}
    names = {identifier: _first_choice(source) for identifier, source in by_id.items()}

    groups: dict[tuple[str, str], list[str]] = defaultdict(list)
    for identifier, name in names.items():
        room = by_id[identifier].room.strip().casefold()
        groups[(room, name.casefold())].append(identifier)

    for group in groups.values():
        if len(group) > 1:
            for number, identifier in enumerate(sorted(group), start=1):
                names[identifier] = f"{names[identifier]} {number}"

    return names
