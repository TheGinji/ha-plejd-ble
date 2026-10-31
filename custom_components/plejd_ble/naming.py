"""Namen voor Plejd-apparaten, zonder lege namen en zonder dubbelen per kamer."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass


@dataclass(frozen=True)
class NameSource:
    """Gegevens uit de Plejd-cloud waarmee we een apparaatnaam bepalen."""

    identifier: str
    title: str
    room: str
    hardware: str


def _first_choice(source: NameSource) -> str:
    """Geef de titel uit de cloud, of anders het model."""
    return source.title.strip() or source.hardware.strip() or "Plejd"


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
