"""Eén Plejd-site: cloudgegevens uit de cache, het Bluetooth-mesh en de apparaten."""

from __future__ import annotations

from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
import inspect
import logging
from typing import Any

from pyplejd import (
    PLEJD_SERVICE,
    AuthenticationError,
    ConnectionError as PlejdConnectionError,
    DeviceTypes,
    PlejdManager,
)
from pyplejd.cloud import PlejdCloudSite
from pyplejd.cloud.site_details import SiteDetails

from homeassistant.components import bluetooth
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import (
    CALLBACK_TYPE,
    CoreState,
    Event,
    HomeAssistant,
    callback,
)
from homeassistant.exceptions import (
    ConfigEntryAuthFailed,
    ConfigEntryNotReady,
    HomeAssistantError,
)
from homeassistant.helpers import device_registry as dr, issue_registry as ir
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.event import async_call_later, async_track_time_interval
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import (
    CACHE_STORE_VERSION,
    CLOUD_CACHE_MAX_AGE,
    CONF_BLOCKED_DEVICES,
    CONF_SITE_ID,
    DOMAIN,
    MANUFACTURER,
    TIME_SYNC_INTERVAL,
)
from .naming import NameSource, build_names
from .signal_quality import (
    RSSI_SAMPLES,
    SIGNAL_MAX_AGE,
    SIGNAL_REFRESH_INTERVAL,
    signal_label,
)

_LOGGER = logging.getLogger(__name__)

type PlejdBleConfigEntry = ConfigEntry[PlejdSite]

# Na een mislukte verbindingspoging proberen we het na deze aantallen seconden
# opnieuw. Daarna nemen de gewone controles, elke paar minuten, het over.
RECONNECT_DELAYS = (10, 30, 60, 120)


@dataclass(frozen=True)
class SignalReading:
    """Het laatst gemeten signaal van een Plejd-apparaat."""

    rssi: int
    seen_at: datetime


def cache_store(hass: HomeAssistant, entry_id: str) -> Store[dict[str, Any]]:
    """Geef de opslag waarin de sitegegevens lokaal worden bewaard."""
    return Store(hass, CACHE_STORE_VERSION, f"{DOMAIN}.{entry_id}")


class CachedCloudSite(PlejdCloudSite):
    """PlejdCloudSite die de cloud alleen aanroept als dat nodig is.

    pyplejd haalt de sitegegevens bij elke start uit de cloud en gebruikt de
    bewaarde gegevens alleen als dat mislukt. Wij draaien dat om: met een
    verse cache wordt de cloud niet aangeroepen.
    """

    def __init__(
        self, username: str, password: str, siteId: str, *, use_cache: bool
    ) -> None:
        """Maak de cloudverbinding aan."""
        super().__init__(username, password, siteId)
        self.use_cache = use_cache
        self.fetched_from_cloud = False

    async def get_details(self) -> None:
        """Haal de sitegegevens uit de cloud en onthoud dat dat gelukt is."""
        await super().get_details()
        self.fetched_from_cloud = True

    async def load_site_details(self, backup: dict[str, Any] | None = None) -> None:
        """Laad de sitegegevens uit de cache of de cloud."""
        if backup and self.use_cache:
            self._details_raw = backup
            self.details = SiteDetails(**backup)
            return
        await super().load_site_details(backup)

    @property
    def raw_details(self) -> dict[str, Any] | None:
        """Geef de sitegegevens zoals ze uit de cloud kwamen."""
        return self._details_raw


class PlejdSite:
    """Eén Plejd-site, gekoppeld aan één configuratie-item."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Maak de site aan, zonder iets te verbinden."""
        self.hass = hass
        self.entry = entry
        self._store = cache_store(hass, entry.entry_id)
        self.manager = PlejdManager(
            username=entry.data[CONF_USERNAME],
            password=entry.data[CONF_PASSWORD],
            siteId=entry.data[CONF_SITE_ID],
        )
        self.manager.blacklist = entry.options.get(CONF_BLOCKED_DEVICES, [])
        self.devices: list[Any] = []
        self.scenes: list[DeviceTypes.PlejdScene] = []
        self.names: dict[str, str] = {}
        self.cache_fetched_at: datetime | None = None
        self.used_cloud = False
        self.started = False
        # Per Bluetooth-adres wat we zelf het laatst hebben gemeten. We gebruiken
        # niet het rssi-veld van pyplejd, want dat bewaart de sterkste waarde ooit.
        self.signal: dict[str, SignalReading] = {}
        self._rssi_history: dict[str, deque[int]] = {}
        self.connection_events: deque[tuple[datetime, bool]] = deque(maxlen=20)
        self.ping_failures = 0
        self.last_ping_failure: datetime | None = None
        self.unconfirmed_commands = 0
        self.last_unconfirmed_command: datetime | None = None
        self.commands_sent = 0
        self.commands_confirmed = 0
        self.commands_unchanged = 0
        self.commands_superseded = 0
        self.confirm_seconds_total = 0.0
        self.confirm_seconds_max = 0.0
        self._failed_pings_in_a_row = 0
        self._cancel_reconnect: CALLBACK_TYPE | None = None
        self._stopping = False
        self._unsubs: list[CALLBACK_TYPE] = []
        self._connection_listeners: list[Callable[[], None]] = []

    async def async_load(self) -> None:
        """Laad de sitegegevens: bij een herstart uit de bewaarde lijst, anders uit de cloud."""
        cached = await self._store.async_load()
        data: dict[str, Any] | None = None
        if isinstance(cached, dict) and isinstance(cached.get("data"), dict):
            data = cached["data"]
            self.cache_fetched_at = dt_util.parse_datetime(
                cached.get("fetched_at") or ""
            )

        # Bij een herstart van Home Assistant gebruiken we de bewaarde lijst, zodat
        # de cloud zo weinig mogelijk wordt aangeroepen. Laadt iemand de integratie
        # zelf opnieuw, dan draait Home Assistant al en willen we de nieuwste lijst,
        # bijvoorbeeld na het toevoegen van een lamp in de Plejd-app.
        starting_up = self.hass.state is not CoreState.running
        use_cache = (
            data is not None
            and starting_up
            and self.cache_fetched_at is not None
            and dt_util.utcnow() - self.cache_fetched_at < CLOUD_CACHE_MAX_AGE
        )

        cloud = CachedCloudSite(**self.manager.credentials, use_cache=use_cache)
        self.manager.cloud = cloud
        try:
            await self.manager.init(data)
        except AuthenticationError as err:
            raise ConfigEntryAuthFailed from err
        except PlejdConnectionError as err:
            raise ConfigEntryNotReady from err

        self.used_cloud = cloud.fetched_from_cloud
        if cloud.fetched_from_cloud:
            self.cache_fetched_at = dt_util.utcnow()
            await self._store.async_save(
                {
                    "fetched_at": self.cache_fetched_at.isoformat(),
                    "data": cloud.raw_details,
                }
            )

        self._build_devices()
        self._update_cloud_issue()

    @callback
    def _update_cloud_issue(self) -> None:
        """Meld het als de apparatenlijst al lang niet meer is ververst."""
        issue_id = f"cloud_unreachable_{self.entry.entry_id}"
        fresh = (
            self.cache_fetched_at is not None
            and dt_util.utcnow() - self.cache_fetched_at < CLOUD_CACHE_MAX_AGE
        )
        if fresh:
            ir.async_delete_issue(self.hass, DOMAIN, issue_id)
        else:
            ir.async_create_issue(
                self.hass,
                DOMAIN,
                issue_id,
                is_fixable=False,
                severity=ir.IssueSeverity.WARNING,
                translation_key="cloud_unreachable",
            )

    def _build_devices(self) -> None:
        """Bepaal welke apparaten en scènes we gebruiken en hoe de apparaten heten."""
        self.devices = [
            device
            for device in self.manager.devices
            if isinstance(device, DeviceTypes.PlejdDevice)
            and not device.deviceData.hiddenFromIntegrations
        ]
        self.scenes = [
            scene
            for scene in self.manager.devices
            if isinstance(scene, DeviceTypes.PlejdScene) and not scene.hidden
        ]
        sources: dict[str, NameSource] = {}
        for device in self.devices:
            if device.outputType:
                sources.setdefault(
                    device.device_identifier,
                    NameSource(
                        identifier=device.device_identifier,
                        title=device.name or "",
                        room=device.room or "",
                        hardware=device.hardware,
                    ),
                )
        self.names = build_names(list(sources.values()))

    def raise_if_not_connected(self) -> None:
        """Geef een duidelijke fout als er geen Bluetooth-verbinding is.

        pyplejd negeert opdrachten zonder verbinding stilletjes, dus dat
        controleren we zelf.
        """
        if not self.manager.connected:
            raise HomeAssistantError(
                translation_domain=DOMAIN, translation_key="not_connected"
            )

    def devices_of_type(self, output_type: DeviceTypes.PlejdDeviceType) -> list[Any]:
        """Geef alle apparaten van een bepaald type."""
        return [d for d in self.devices if d.outputType == output_type]

    def device_registry_fields(self, device: Any) -> dict[str, Any]:
        """Beschrijf een apparaat voor het apparaatregister, als gewone velden.

        We gebruiken hier bewust geen DeviceInfo: dat is vanaf Home Assistant
        2026.11 geen woordenboek meer en kan dus niet met ** worden uitgepakt.
        """
        fields: dict[str, Any] = {
            "identifiers": {(DOMAIN, device.device_identifier)},
            "name": self.names[device.device_identifier],
            "manufacturer": MANUFACTURER,
            "model": device.hardware,
            "suggested_area": device.room or None,
            "sw_version": str(device.firmware),
        }
        if device.parent_identifier == device.device_identifier:
            fields["connections"] = {(dr.CONNECTION_BLUETOOTH, device.ble_mac)}
        return fields

    def entity_device_info(self, device: Any) -> DeviceInfo:
        """Verwijs vanuit een entiteit naar het apparaat dat al is aangemaakt."""
        return DeviceInfo(identifiers={(DOMAIN, device.device_identifier)})

    @callback
    def async_register_devices(self) -> None:
        """Zet alle apparaten in het register, hoofdapparaten eerst."""
        registry = dr.async_get(self.hass)
        # Nieuwere versies van Home Assistant willen via_device_id in plaats
        # van via_device; oudere kennen dat nog niet.
        uses_via_device_id = (
            "via_device_id" in inspect.signature(registry.async_get_or_create).parameters
        )
        created: dict[str, dr.DeviceEntry] = {}
        ordered = sorted(
            (d for d in self.devices if d.outputType),
            key=lambda d: d.parent_identifier != d.device_identifier,
        )
        for device in ordered:
            identifier = device.device_identifier
            if identifier in created:
                continue
            fields = self.device_registry_fields(device)
            parent = device.parent_identifier
            if parent != identifier and parent in self.names:
                if uses_via_device_id:
                    fields["via_device_id"] = created[parent].id
                else:
                    fields["via_device"] = (DOMAIN, parent)
            created[identifier] = registry.async_get_or_create(
                config_entry_id=self.entry.entry_id, **fields
            )

    def hub_device_info(self) -> DeviceInfo:
        """Beschrijf het apparaat voor de site zelf, met de knop en de sensor."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.entry.entry_id)},
            name="Plejd BLE",
            manufacturer=MANUFACTURER,
            entry_type=dr.DeviceEntryType.SERVICE,
        )

    def powered_units(self) -> dict[str, Any]:
        """Geef per apparaat op netstroom één apparaat, met het Bluetooth-adres als sleutel.

        Een fysiek apparaat kan meerdere uitgangen hebben. Dan kiezen we het
        hoofdapparaat om het te vertegenwoordigen.
        """
        units: dict[str, Any] = {}
        for device in self.devices:
            if not device.outputType or not device.powered:
                continue
            is_primary = device.parent_identifier == device.device_identifier
            if device.BLEaddress in units and not is_primary:
                continue
            units[device.BLEaddress] = device
        return units

    def gateway_candidates(self) -> dict[str, str]:
        """Geef de apparaten op netstroom die als Bluetooth-ingang kunnen dienen.

        De sleutel is het Bluetooth-adres zoals pyplejd het gebruikt, de waarde
        een leesbare naam.
        """
        candidates: dict[str, str] = {}
        for address, device in self.powered_units().items():
            name = self.names[device.device_identifier]
            candidates[address] = f"{name} ({device.room})" if device.room else name
        return candidates

    def average_rssi(self, address: str) -> int | None:
        """Geef het gemiddelde van de laatste metingen, of niets zonder recente meting."""
        reading = self.signal.get(address)
        history = self._rssi_history.get(address)
        if (
            reading is None
            or not history
            or dt_util.utcnow() - reading.seen_at > SIGNAL_MAX_AGE
        ):
            return None
        return round(sum(history) / len(history))

    def gateway_choices(self) -> dict[str, str]:
        """Geef de Bluetooth-ingangen met hun signaalsterkte, voor het optiesscherm."""
        names = self.gateway_candidates()
        return {
            address: (
                f"{signal_label(self.average_rssi(device.ble_mac.upper()))}  "
                f"{names[address]}"
            )
            for address, device in self.powered_units().items()
        }

    def connected_via(self) -> str | None:
        """Geef de naam van het apparaat waarlangs we nu verbonden zijn.

        pyplejd wist de markering is_gateway niet als de verbinding naar een ander
        apparaat wisselt, dus die kunnen we niet gebruiken. We vragen het aan de
        verbinding zelf.
        """
        node = getattr(self.manager.mesh, "_gateway_node", None)
        if node is None or not self.manager.connected:
            return None
        return self.gateway_candidates().get(node.BLEaddress)

    @callback
    def note_command(self) -> None:
        """Onthoud dat we een opdracht naar een apparaat hebben gestuurd."""
        self.commands_sent += 1

    @callback
    def note_confirmed_command(self, seconds: float) -> None:
        """Onthoud dat een apparaat een opdracht bevestigde, en hoe lang dat duurde."""
        self.commands_confirmed += 1
        self.confirm_seconds_total += seconds
        self.confirm_seconds_max = max(self.confirm_seconds_max, seconds)

    @callback
    def note_superseded_command(self) -> None:
        """Onthoud dat een nieuwe opdracht kwam voordat de vorige bevestigd was."""
        self.commands_superseded += 1

    @callback
    def note_unchanged_command(self) -> None:
        """Onthoud dat een opdracht niets veranderde en het apparaat dus zweeg."""
        self.commands_unchanged += 1

    @callback
    def note_unconfirmed_command(self) -> None:
        """Onthoud dat een apparaat een opdracht niet binnen enkele seconden bevestigde."""
        self.unconfirmed_commands += 1
        self.last_unconfirmed_command = dt_util.utcnow()

    @property
    def average_confirm_seconds(self) -> float | None:
        """Geef de gemiddelde tijd tot een bevestiging, of niets zonder bevestigingen."""
        if not self.commands_confirmed:
            return None
        return round(self.confirm_seconds_total / self.commands_confirmed, 2)

    @callback
    def async_add_connection_listener(
        self, listener: Callable[[], None]
    ) -> Callable[[], None]:
        """Laat weten als de Bluetooth-verbinding aan of uit gaat."""
        self._connection_listeners.append(listener)

        @callback
        def remove() -> None:
            self._connection_listeners.remove(listener)

        return remove

    async def async_apply_options(self) -> None:
        """Pas de gekozen Bluetooth-ingangen toe, zonder opnieuw te laden."""
        blocked = self.entry.options.get(CONF_BLOCKED_DEVICES, [])
        await self.manager.set_blacklist(blocked)

    @callback
    def async_request_refresh(self) -> None:
        """Laad de integratie opnieuw, zodat de apparatenlijst vers wordt opgehaald.

        Lukt het ophalen niet, dan blijft de bewaarde lijst in gebruik.
        """
        self.hass.config_entries.async_schedule_reload(self.entry.entry_id)

    async def async_start(self) -> None:
        """Begin met Bluetooth: ontdek het mesh en houd de verbinding open."""
        await self._async_close_stale_connections()

        self._unsubs.append(
            bluetooth.async_register_callback(
                self.hass,
                self._async_discovered,
                bluetooth.BluetoothCallbackMatcher(
                    connectable=True, service_uuid=PLEJD_SERVICE.lower()
                ),
                bluetooth.BluetoothScanningMode.PASSIVE,
            )
        )
        for service_info in bluetooth.async_discovered_service_info(self.hass, True):
            if PLEJD_SERVICE.lower() in service_info.advertisement.service_uuids:
                self._async_discovered(service_info, None, connect=False)

        self._unsubs.append(
            async_track_time_interval(
                self.hass,
                self._async_ping,
                self.manager.ping_interval,
                name="Plejd BLE keep-alive",
            )
        )
        self._unsubs.append(
            async_track_time_interval(
                self.hass,
                self._async_broadcast_time,
                TIME_SYNC_INTERVAL,
                name="Plejd BLE klok",
            )
        )
        self._unsubs.append(
            async_track_time_interval(
                self.hass,
                self._async_refresh_signal,
                SIGNAL_REFRESH_INTERVAL,
                name="Plejd BLE signaal",
            )
        )
        self.manager.connection_monitor = self._connection_monitor
        self.started = True

        self.entry.async_create_background_task(
            self.hass, self._async_ping(), "plejd_ble eerste verbinding"
        )
        self.entry.async_create_background_task(
            self.hass, self._async_broadcast_time(), "plejd_ble eerste klokcontrole"
        )

    async def async_stop(self) -> None:
        """Stop alles en verbreek de Bluetooth-verbinding."""
        self._stopping = True
        for unsub in self._unsubs:
            unsub()
        self._unsubs.clear()
        if self._cancel_reconnect is not None:
            self._cancel_reconnect()
            self._cancel_reconnect = None
        await self.manager.disconnect()

    async def async_hass_stopping(self, _event: Event) -> None:
        """Verbreek de verbinding netjes als Home Assistant stopt."""
        self._stopping = True
        await self.manager.disconnect()

    async def _async_close_stale_connections(self) -> None:
        """Sluit verbindingen die nog openstaan van een eerdere sessie."""
        done: set[str] = set()
        for device in self.devices:
            if device.ble_mac in done:
                continue
            done.add(device.ble_mac)
            ble_device = bluetooth.async_ble_device_from_address(
                self.hass, device.ble_mac, True
            )
            if ble_device:
                await self.manager.close_stale(ble_device)

    @callback
    def _async_discovered(
        self,
        service_info: bluetooth.BluetoothServiceInfoBleak,
        _change: bluetooth.BluetoothChange | None = None,
        *,
        connect: bool = True,
    ) -> None:
        """Geef een gevonden Plejd-apparaat door aan pyplejd en onthoud het signaal."""
        address = service_info.device.address.upper()
        self.signal[address] = SignalReading(service_info.rssi, dt_util.utcnow())
        self._rssi_history.setdefault(address, deque(maxlen=RSSI_SAMPLES)).append(
            service_info.rssi
        )
        is_new = self.manager.add_mesh_device(service_info.device, service_info.rssi)
        if connect and is_new and not self._stopping:
            self.entry.async_create_background_task(
                self.hass, self._async_ping(), "plejd_ble nieuw apparaat gevonden"
            )

    @callback
    def _async_refresh_signal(self, _now: datetime) -> None:
        """Vraag Home Assistant om het volgende bericht van elk apparaat door te geven.

        Home Assistant geeft een bericht dat precies gelijk is aan het vorige niet
        door, en Plejd-apparaten sturen steeds hetzelfde. Zonder dit zouden we
        alleen de allereerste meting van elk apparaat zien.
        """
        for device in self.powered_units().values():
            bluetooth.async_clear_advertisement_history(
                self.hass, device.ble_mac.upper()
            )

    def _connection_monitor(self, connected: bool) -> None:
        """Onthoud verbindingswijzigingen en probeer opnieuw te verbinden bij uitval."""
        self.connection_events.append((dt_util.utcnow(), connected))
        for listener in list(self._connection_listeners):
            listener()
        if self._stopping or connected:
            return
        self.entry.async_create_background_task(
            self.hass, self._async_ping(), "plejd_ble opnieuw verbinden"
        )

    async def _async_ping(self, *_: Any) -> None:
        """Verbind met het mesh of houd de verbinding in leven."""
        if self._stopping or not self.started:
            return
        if await self.manager.ping():
            if self._failed_pings_in_a_row >= 2:
                _LOGGER.info("De verbinding met het Plejd-mesh is hersteld")
            self._failed_pings_in_a_row = 0
            return
        self.ping_failures += 1
        self.last_ping_failure = dt_util.utcnow()
        self._failed_pings_in_a_row += 1
        _LOGGER.debug("Ping naar het Plejd-mesh mislukt")
        if self.manager.connected:
            await self._async_drop_dead_connection()
        if self._failed_pings_in_a_row == 2:
            seen = sum(
                1
                for device in self.powered_units().values()
                if device.ble_mac.upper() in self.signal
            )
            _LOGGER.warning(
                "Geen verbinding met het Plejd-mesh. Home Assistant ziet %s van de %s "
                "apparaten op netstroom. We blijven het proberen",
                seen,
                len(self.powered_units()),
            )
        self._schedule_reconnect()

    async def _async_drop_dead_connection(self) -> None:
        """Verbreek een verbinding die open lijkt, maar niet meer antwoordt.

        pyplejd merkt niet als de verbinding wegvalt: het blijft denken dat hij open
        staat en probeert nooit opnieuw. Door hem zelf te verbreken, maakt de
        verbindingsbewaking meteen een nieuwe.
        """
        _LOGGER.warning(
            "De Bluetooth-verbinding met %s reageert niet meer. We maken hem opnieuw",
            self.connected_via() or "het Plejd-mesh",
        )
        await self.manager.disconnect()

    @callback
    def _schedule_reconnect(self) -> None:
        """Probeer het snel opnieuw, met steeds iets langere pauzes."""
        if self._cancel_reconnect is not None or self._stopping:
            return
        index = max(min(self._failed_pings_in_a_row, len(RECONNECT_DELAYS)), 1) - 1
        self._cancel_reconnect = async_call_later(
            self.hass, RECONNECT_DELAYS[index], self._async_reconnect
        )

    async def _async_reconnect(self, _now: datetime) -> None:
        """Doe de geplande nieuwe verbindingspoging."""
        self._cancel_reconnect = None
        await self._async_ping()

    async def _async_broadcast_time(self, *_: Any) -> None:
        """Controleer of de klok van het mesh klopt."""
        if self._stopping:
            return
        await self.manager.broadcast_time()
