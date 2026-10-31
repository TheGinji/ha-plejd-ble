"""Controle dat pyplejd nog zo is opgebouwd als wij verwachten.

We overschrijven een stukje van pyplejd en gebruiken een paar interne namen.
Deze tests laten meteen zien als een nieuwe versie dat verandert.
"""

from __future__ import annotations

import inspect

from pyplejd import PlejdManager
from pyplejd.cloud import PlejdCloudSite
from pyplejd.cloud.site_details import SiteDetails
from pyplejd.interface.plejd_light import PlejdLight
from pyplejd.interface.plejd_relay import PlejdRelay

from custom_components.plejd_ble.site import CachedCloudSite


def parameters(function: object) -> list[str]:
    """Geef de namen van de parameters van een functie."""
    return list(inspect.signature(function).parameters)


def test_cloud_site_interface_is_unchanged() -> None:
    """De methoden die we overschrijven hebben nog dezelfde vorm."""
    assert parameters(PlejdCloudSite.__init__)[:4] == [
        "self",
        "username",
        "password",
        "siteId",
    ]
    assert parameters(PlejdCloudSite.load_site_details) == ["self", "backup"]
    assert parameters(PlejdCloudSite.get_details) == ["self"]
    assert inspect.iscoroutinefunction(PlejdCloudSite.get_details)
    assert inspect.iscoroutinefunction(PlejdCloudSite.load_site_details)
    assert issubclass(CachedCloudSite, PlejdCloudSite)
    assert SiteDetails.model_fields


def test_manager_interface_is_unchanged() -> None:
    """De manager heeft nog de onderdelen waar wij op leunen."""
    manager = PlejdManager("gebruiker@example.com", "wachtwoord", "site-1")

    for name in (
        "cloud",
        "credentials",
        "devices",
        "connection_monitor",
        "ping_interval",
        "connected",
        "mesh",
    ):
        assert hasattr(manager, name), name
    for name in (
        "init",
        "ping",
        "broadcast_time",
        "disconnect",
        "close_stale",
        "add_mesh_device",
    ):
        assert callable(getattr(manager, name)), name


def test_device_commands_are_unchanged() -> None:
    """De opdrachten naar lampen en relais hebben nog dezelfde vorm."""
    assert parameters(PlejdLight.turn_on) == ["self", "dim", "colortemp"]
    assert parameters(PlejdLight.turn_off) == ["self"]
    assert parameters(PlejdRelay.turn_on) == ["self"]
    assert parameters(PlejdRelay.turn_off) == ["self"]
