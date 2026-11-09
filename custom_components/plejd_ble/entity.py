"""Basisklasse voor alle Plejd BLE-entiteiten."""

from __future__ import annotations

from datetime import datetime
import time
from typing import Any

from homeassistant.core import CALLBACK_TYPE, callback
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.event import async_call_later

from .site import PlejdSite

# Zo lang tonen we wat we gevraagd hebben als het apparaat het niet bevestigt.
ASSUMED_STATE_TIMEOUT = 5
# Plejd rondt de helderheid soms af, dus zoveel verschil telt nog als bevestiging.
ASSUMED_BRIGHTNESS_TOLERANCE = 3
# Komt de bevestiging na het verlopen van de wachttijd, maar binnen zoveel seconden na de
# opdracht, dan tellen we haar als te laat. Daarna beschouwen we haar als toeval.
LATE_CONFIRM_WINDOW = 30


class PlejdEntity(Entity):
    """Een entiteit die bij één Plejd-apparaat hoort.

    Een apparaat meldt zijn nieuwe stand pas na ongeveer een seconde. Na een
    opdracht tonen we daarom direct wat we gevraagd hebben (de aangenomen stand).
    Zodra het apparaat dat bevestigt neemt de echte stand het weer over. Komt er
    binnen enkele seconden geen bevestiging, dan vallen we terug op de laatst
    gemelde stand, zodat de tegel nooit blijft liegen.
    """

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, site: PlejdSite, device: Any) -> None:
        """Koppel de entiteit aan een apparaat uit pyplejd."""
        self._site = site
        self._device = device
        self._data: dict[str, Any] = {}
        self._assumed: dict[str, Any] = {}
        self._cancel_assumed: CALLBACK_TYPE | None = None
        self._assumed_at = 0.0
        self._assumed_unchanged = False
        self._expired: dict[str, Any] = {}
        self._attr_unique_id = ":".join(device.identifier)
        self._attr_device_info = site.entity_device_info(device)
        self._attr_entity_registry_visible_default = not device.hidden

    @property
    def available(self) -> bool:
        """De entiteit is beschikbaar zolang het Bluetooth-mesh verbonden is."""
        return self._site.manager.connected

    def _value(self, key: str) -> Any:
        """Geef de waarde die we tonen: eerst de aangenomen stand, dan de gemelde."""
        if key in self._assumed:
            return self._assumed[key]
        return self._data.get(key)

    async def async_added_to_hass(self) -> None:
        """Luister naar wijzigingen van het apparaat."""
        self.async_on_remove(self._device.subscribe(self._async_device_updated))
        self.async_on_remove(self._clear_assumed_timer)

    @callback
    def _async_device_updated(self, data: dict[str, Any]) -> None:
        """Verwerk een nieuwe status van het apparaat."""
        self._data = data
        if self._assumed and self._confirms_assumed(data):
            self._site.note_confirmed_command(time.monotonic() - self._assumed_at)
            self._clear_assumed()
        elif self._expired:
            seconds = time.monotonic() - self._assumed_at
            if seconds > LATE_CONFIRM_WINDOW:
                self._expired = {}
            elif self._matches(self._expired, data):
                self._site.note_late_confirmed_command(seconds)
                self._expired = {}
        self._handle_device_update(data)
        self.async_write_ha_state()

    @callback
    def _handle_device_update(self, data: dict[str, Any]) -> None:
        """Laat subklassen op een wijziging reageren."""

    def _confirms_assumed(self, data: dict[str, Any]) -> bool:
        """Controleer of de melding van het apparaat is wat we gevraagd hebben."""
        return self._matches(self._assumed, data)

    @staticmethod
    def _matches(wanted_values: dict[str, Any], data: dict[str, Any]) -> bool:
        """Controleer of een melding van het apparaat overeenkomt met wat we vroegen."""
        for key, wanted in wanted_values.items():
            reported = data.get(key)
            if reported is None:
                return False
            if key == "dim":
                if abs(int(reported) - int(wanted)) > ASSUMED_BRIGHTNESS_TOLERANCE:
                    return False
            elif reported != wanted:
                return False
        return True

    @callback
    def _async_assume(self, **values: Any) -> None:
        """Toon direct wat we gevraagd hebben, in afwachting van het apparaat."""
        if self._cancel_assumed is not None:
            self._site.note_superseded_command()
        self._site.note_command()
        self._expired = {}
        self._assumed = values
        # Stond de lamp al zo, dan meldt het apparaat misschien niets. Dat is geen fout.
        self._assumed_unchanged = self._confirms_assumed(self._data)
        self._assumed_at = time.monotonic()
        self._clear_assumed_timer()
        self._cancel_assumed = async_call_later(
            self.hass, ASSUMED_STATE_TIMEOUT, self._async_assumed_expired
        )
        self.async_write_ha_state()

    @callback
    def _async_assumed_expired(self, _now: datetime) -> None:
        """Val terug op de gemelde stand als het apparaat niets bevestigde."""
        self._cancel_assumed = None
        wanted = self._assumed
        self._assumed = {}
        if self._site.manager.connected:
            if self._assumed_unchanged:
                self._site.note_unchanged_command()
            else:
                self._site.note_unconfirmed_command()
                self._expired = wanted
        self.async_write_ha_state()

    @callback
    def _clear_assumed(self) -> None:
        """Stop met de aangenomen stand."""
        self._assumed = {}
        self._clear_assumed_timer()

    @callback
    def _clear_assumed_timer(self) -> None:
        """Annuleer de wachttijd, als die loopt."""
        if self._cancel_assumed is not None:
            self._cancel_assumed()
            self._cancel_assumed = None

    def _raise_if_not_connected(self) -> None:
        """Geef een duidelijke fout als er geen Bluetooth-verbinding is."""
        self._site.raise_if_not_connected()
