"""Tests voor de naamgeving van apparaten."""

from __future__ import annotations

from custom_components.plejd_ble.naming import NameSource, build_names


def source(identifier: str, title: str, room: str, hardware: str = "WPH-01-LC"):
    """Maak een naambron met verzonnen gegevens."""
    return NameSource(identifier, title, room, hardware)


def test_unique_titles_stay_unchanged() -> None:
    """Een titel die maar één keer voorkomt, blijft zoals hij is."""
    names = build_names(
        [source("a", "Zithoek", "Woonkamer"), source("b", "Eettafel", "Woonkamer")]
    )
    assert names == {"a": "Zithoek", "b": "Eettafel"}


def test_same_title_in_different_rooms_stays_unchanged() -> None:
    """De kamer zit niet in de naam, want Home Assistant zet die zelf voor de ID."""
    names = build_names(
        [
            source("a", "Plafondlicht", "Slaapkamer 1"),
            source("b", "Plafondlicht", "Slaapkamer 2"),
            source("c", "Plafondlicht", ""),
        ]
    )
    assert names == {"a": "Plafondlicht", "b": "Plafondlicht", "c": "Plafondlicht"}


def test_same_title_in_the_same_room_gets_a_number() -> None:
    """Twee apparaten met dezelfde naam in dezelfde kamer worden genummerd."""
    names = build_names(
        [source("b", "Spot", "Keuken"), source("a", "Spot", "Keuken"), source("c", "Spot", "Hal")]
    )
    assert names == {"a": "Spot 1", "b": "Spot 2", "c": "Spot"}


def test_unnamed_devices_use_the_model() -> None:
    """Zonder titel gebruiken we het model, genummerd bij dubbelen in een kamer."""
    names = build_names(
        [source("b", "", "Hal"), source("a", "", "Hal"), source("c", "", "Keuken")]
    )
    assert names == {"a": "WPH-01-LC 1", "b": "WPH-01-LC 2", "c": "WPH-01-LC"}


def test_nothing_known_falls_back_to_plejd() -> None:
    """Zonder titel en model heet het apparaat Plejd."""
    assert build_names([source("a", "  ", "", "")]) == {"a": "Plejd"}


def test_result_does_not_depend_on_order() -> None:
    """De volgorde van de invoer verandert de namen niet."""
    sources = [source("b", "", "Hal"), source("a", "", "Hal")]
    assert build_names(sources) == build_names(list(reversed(sources)))


def test_duplicates_ignore_letter_case() -> None:
    """Hoofdletters maken een naam niet uniek."""
    names = build_names([source("a", "plafond", "Keuken"), source("b", "Plafond", "Keuken")])
    assert names == {"a": "plafond 1", "b": "Plafond 2"}
