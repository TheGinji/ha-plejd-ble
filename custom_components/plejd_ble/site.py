"""Eén Plejd-site: cloudgegevens uit de cache, het Bluetooth-mesh en de apparaten."""

from __future__ import annotations

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
from homeassistant.core import CALLBACK_TYPE, Event, HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import (
    CACHE_STORE_VERSION,
    CLOUD_CACHE_MAX_AGE,
    CONF_SITE_ID,
    DOMAIN,
    MANUFACTURER,
    TIME_SYNC_INTERVAL,
)
from .naming import NameSource, build_names

_LOGGER = logging.getLogger(__name__)

type PlejdBleConfigEntry = ConfigEntry[PlejdSite]


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
        self._store: Store[dict[str, Any]] = Store(
            hass, CACHE_STORE_VERSION, f"{DOMAIN}.{entry.entry_id}"
        )
        self.manager = PlejdManager(
            username=entry.data[CONF_USERNAME],
            password=entry.data[CONF_PASSWORD],
            siteId=entry.data[CONF_SITE_ID],
        )
        self.devices: list[Any] = []
        self.names: dict[str, str] = {}
        self.cache_fetched_at: datetime | None = None
        self.used_cloud = False
        self.started = False
        self._stopping = False
        self._unsubs: list[CALLBACK_TYPE] = []

    async def async_load(self) -> None:
        """Laad de sitegegevens: uit de cache als die vers is, anders uit de cloud."""
        cached = await self._store.async_load()
        data: dict[str, Any] | None = None
        if isinstance(cached, dict) and isinstance(cached.get("data"), dict):
            data = cached["data"]
            self.cache_fetched_at = dt_util.parse_datetime(
                cached.get("fetched_at") or ""
            )

        use_cache = (
            data is not None
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

    def _build_devices(self) -> None:
        """Bepaal welke apparaten we gebruiken en hoe ze heten."""
        self.devices = [
            device
            for device in self.manager.devices
            if isinstance(device, DeviceTypes.PlejdDevice)
            and not device.deviceData.hiddenFromIntegrations
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

    def devices_of_type(self, output_type: DeviceTypes.PlejdDeviceType) -> list[Any]:
        """Geef alle apparaten van een bepaald type."""
        return [d for d in self.devices if d.outputType == output_type]

    def device_info(self, device: Any) -> DeviceInfo:
        """Beschrijf een apparaat voor het apparaatregister."""
        info = DeviceInfo(
            identifiers={(DOMAIN, device.device_identifier)},
            name=self.names[device.device_identifier],
            manufacturer=MANUFACTURER,
            model=device.hardware,
            suggested_area=device.room or None,
            sw_version=str(device.firmware),
        )
        if device.parent_identifier == device.device_identifier:
            info["connections"] = {(dr.CONNECTION_BLUETOOTH, device.ble_mac)}
        elif device.parent_identifier in self.names:
            info["via_device"] = (DOMAIN, device.parent_identifier)
        return info

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
            info = self.device_info(device)
            via_device = info.pop("via_device", None)
            extra: dict[str, Any] = {}
            if via_device is not None:
                if uses_via_device_id:
                    extra["via_device_id"] = created[via_device[1]].id
                else:
                    extra["via_device"] = via_device
            created[identifier] = registry.async_get_or_create(
                config_entry_id=self.entry.entry_id, **info, **extra
            )

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
        """Geef een gevonden Plejd-apparaat door aan pyplejd."""
        is_new = self.manager.add_mesh_device(service_info.device, service_info.rssi)
        if connect and is_new and not self._stopping:
            self.entry.async_create_background_task(
                self.hass, self._async_ping(), "plejd_ble nieuw apparaat gevonden"
            )

    def _connection_monitor(self, connected: bool) -> None:
        """Probeer opnieuw te verbinden als de verbinding wegvalt."""
        if self._stopping or connected:
            return
        self.entry.async_create_background_task(
            self.hass, self._async_ping(), "plejd_ble opnieuw verbinden"
        )

    async def _async_ping(self, *_: Any) -> None:
        """Verbind met het mesh of houd de verbinding in leven."""
        if self._stopping or not self.started:
            return
        if not await self.manager.ping():
            _LOGGER.debug("Ping naar het Plejd-mesh mislukt")

    async def _async_broadcast_time(self, *_: Any) -> None:
        """Controleer of de klok van het mesh klopt."""
        if self._stopping:
            return
        await self.manager.broadcast_time()
