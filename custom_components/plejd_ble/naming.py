"""Namen voor Plejd-apparaten, zonder lege of dubbele namen."""

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
    """Geef de titel uit de cloud, of anders ruimte plus model."""
    if title := source.title.strip():
        return title
    parts = [part for part in (source.room.strip(), source.hardware.strip()) if part]
    return " ".join(parts) or "Plejd"


def _with_room(source: NameSource) -> str:
    """Zet de ruimte voor de titel, tenzij die er al in staat."""
    title = source.title.strip()
    room = source.room.strip()
    if not title or not room or room.lower() in title.lower():
        return _first_choice(source)
    return f"{room} {title}"


def _duplicates(names: dict[str, str]) -> list[list[str]]:
    """Geef groepen identifiers die dezelfde naam hebben."""
    groups: dict[str, list[str]] = defaultdict(list)
    for identifier, name in names.items():
        groups[name.casefold()].append(identifier)
    return [sorted(group) for group in groups.values() if len(group) > 1]


def build_names(sources: list[NameSource]) -> dict[str, str]:
    """Bepaal per apparaat een naam die uniek en voorspelbaar is.

    Zo worden entiteit-ID's niet "plafondlicht_2" en "plafondlicht_3", maar
    "slaapkamer_1_plafondlicht" en "slaapkamer_2_plafondlicht".
    """
    by_id = {source.identifier: source for source in sources}
    names = {identifier: _first_choice(source) for identifier, source in by_id.items()}

    # Stap 1: dubbele titels krijgen de ruimte ervoor.
    for group in _duplicates(names):
        for identifier in group:
            names[identifier] = _with_room(by_id[identifier])

    # Stap 2: wat dan nog dubbel is, krijgt een volgnummer.
    for group in _duplicates(names):
        for number, identifier in enumerate(group, start=1):
            names[identifier] = f"{names[identifier]} {number}"

    return names
