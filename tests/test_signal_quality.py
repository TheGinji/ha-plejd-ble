"""Tests voor het tonen van de signaalsterkte in de opties."""

from __future__ import annotations

from datetime import timedelta
from types import SimpleNamespace

from freezegun.api import FrozenDateTimeFactory
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.core import HomeAssistant

from custom_components.plejd_ble.signal_quality import signal_label

GREEN = "\U0001F7E2"
ORANGE = "\U0001F7E0"
RED = "\U0001F534"
WHITE = "\u26AA"
DIMMER_ADDRESS = "A0:B1:C2:00:00:01"
BED_ADDRESS = "A0:B1:C2:00:00:02"


def service_info(address: str, rssi: int) -> SimpleNamespace:
    """Maak een verzonnen Bluetooth-melding van een Plejd-apparaat."""
    return SimpleNamespace(device=SimpleNamespace(address=address, name="Plejd"), rssi=rssi)


@pytest.mark.parametrize(
    ("rssi", "expected"),
    [
        (-40, f"{GREEN} -40 dBm"),
        (-65, f"{GREEN} -65 dBm"),
        (-66, f"{ORANGE} -66 dBm"),
        (-80, f"{ORANGE} -80 dBm"),
        (-81, f"{RED} -81 dBm"),
        (None, f"{WHITE} \u2013 dBm"),
    ],
)
def test_signal_label_colors(rssi: int | None, expected: str) -> None:
    """Goed is groen, redelijk oranje, slecht rood, en zonder meting wit."""
    assert signal_label(rssi) == expected


async def test_options_show_the_signal_before_the_name(
    hass: HomeAssistant, loaded_entry: MockConfigEntry, mocks: SimpleNamespace
) -> None:
    """In de lijst staat het gemiddelde signaal tussen het vinkje en de naam."""
    callback = mocks.bluetooth.register_callback.call_args.args[1]
    callback(service_info(DIMMER_ADDRESS, -55), None)
    callback(service_info(DIMMER_ADDRESS, -59), None)
    callback(service_info(BED_ADDRESS, -90), None)

    result = await hass.config_entries.options.async_init(loaded_entry.entry_id)
    selector = next(iter(result["data_schema"].schema.values()))
    labels = {option["value"]: option["label"] for option in selector.config["options"]}

    assert labels["A0B1C2000001"] == f"{GREEN} -57 dBm  Zithoek (Woonkamer)"
    assert labels["A0B1C2000002"].startswith(f"{RED} -90 dBm")
    assert labels["A0B1C2000003"].startswith(f"{WHITE} ")


async def test_old_measurements_are_not_shown(
    hass: HomeAssistant,
    loaded_entry: MockConfigEntry,
    mocks: SimpleNamespace,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Een meting van meer dan een kwartier terug telt niet meer als huidig."""
    callback = mocks.bluetooth.register_callback.call_args.args[1]
    callback(service_info(DIMMER_ADDRESS, -60), None)
    site = loaded_entry.runtime_data
    assert site.average_rssi(DIMMER_ADDRESS) == -60

    freezer.tick(timedelta(minutes=16))

    assert site.average_rssi(DIMMER_ADDRESS) is None
