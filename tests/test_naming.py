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


def test_duplicate_titles_get_the_room() -> None:
    """Dezelfde titel in verschillende kamers krijgt de kamer ervoor."""
    names = build_names(
        [
            source("a", "Plafondlicht", "Slaapkamer 1"),
            source("b", "Plafondlicht", "Slaapkamer 2"),
            source("c", "Plafondlicht", "Slaapkamer 3"),
        ]
    )
    assert names["a"] == "Slaapkamer 1 Plafondlicht"
    assert names["b"] == "Slaapkamer 2 Plafondlicht"
    assert len(set(names.values())) == 3


def test_room_already_in_title_gets_a_number() -> None:
    """Staat de kamer al in de titel, dan komt er een volgnummer."""
    names = build_names([source("a", "Hal plafond", "Hal"), source("b", "Hal plafond", "Hal")])
    assert sorted(names.values()) == ["Hal plafond 1", "Hal plafond 2"]


def test_unnamed_devices_use_room_and_model() -> None:
    """Zonder titel gebruiken we kamer en model, genummerd bij dubbelen."""
    names = build_names(
        [source("b", "", "Hal"), source("a", "", "Hal"), source("c", "", "Keuken")]
    )
    assert names["a"] == "Hal WPH-01-LC 1"
    assert names["b"] == "Hal WPH-01-LC 2"
    assert names["c"] == "Keuken WPH-01-LC"


def test_nothing_known_falls_back_to_plejd() -> None:
    """Zonder titel, kamer en model heet het apparaat Plejd."""
    assert build_names([source("a", "  ", "", "")]) == {"a": "Plejd"}


def test_result_does_not_depend_on_order() -> None:
    """De volgorde van de invoer verandert de namen niet."""
    sources = [source("b", "", "Hal"), source("a", "", "Hal")]
    assert build_names(sources) == build_names(list(reversed(sources)))


def test_duplicates_ignore_letter_case() -> None:
    """Hoofdletters maken een naam niet uniek."""
    names = build_names([source("a", "plafond", "Keuken"), source("b", "Plafond", "Toilet")])
    assert names == {"a": "Keuken plafond", "b": "Toilet Plafond"}
