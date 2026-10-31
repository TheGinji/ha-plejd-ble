"""Tests voor de naamgeving van apparaten."""

from __future__ import annotations

from custom_components.plejd_ble.naming import (
    PRODUCT_NAMES,
    NameSource,
    build_names,
    product_name,
)


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


def test_unnamed_devices_use_the_product_name() -> None:
    """Zonder titel gebruiken we de productnaam, genummerd bij dubbelen in een kamer."""
    names = build_names(
        [source("b", "", "Hal"), source("a", "", "Hal"), source("c", "", "Keuken")]
    )
    assert names == {
        "a": "Wireless push button 1",
        "b": "Wireless push button 2",
        "c": "Wireless push button",
    }


def test_unknown_models_keep_their_model_number() -> None:
    """Een model zonder bekende productnaam blijft het modelnummer houden."""
    names = build_names([source("a", "", "Hal", "ABC-99-X"), source("b", "", "Hal", "-UNKNOWN- (7)")])
    assert names == {"a": "ABC-99-X", "b": "-UNKNOWN- (7)"}


def test_product_names_cover_the_whole_model_family() -> None:
    """Varianten van hetzelfde model delen de productnaam."""
    assert product_name("WPH-01-LC") == "Wireless push button"
    assert product_name("WPH-01-A-55W") == "Wireless push button"
    assert product_name("WMS-01") == "Wireless motion sensor"
    assert product_name("LED-75-H") == "LED driver 75 W"
    assert product_name("LED-75-V2") == "LED driver 75 W"
    assert product_name("DWN-02-LC") == "Downlight"
    assert product_name("REL-01-2P") == "Relay 16 A"
    assert product_name("TRM-01-EW") == "Thermostat"


def test_unknown_product_families_keep_their_model_number() -> None:
    """Een familie die niet in de lijst staat, houdt het modelnummer."""
    assert product_name("CCL-01") == "CCL-01"
    assert product_name("XYZ-99-A") == "XYZ-99-A"


def test_product_names_are_clean() -> None:
    """Elke sleutel is een familie als AAA-00 en elke naam is niet leeg."""
    for family, name in PRODUCT_NAMES.items():
        assert len(family) == 6 and family[3] == "-", family
        assert family[:3].isalpha() and family[:3].isupper(), family
        assert family[4:].isdigit(), family
        assert name.strip() == name and name, family


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
