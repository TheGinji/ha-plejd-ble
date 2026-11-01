"""Sensoren: cloudsynchronisatie, batterijniveau en per apparaat signaal en laatst gezien."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from pyplejd import DeviceTypes

from homeassistant.components.sensor import (
    RestoreSensor,
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import SIGNAL_STRENGTH_DECIBELS_MILLIWATT, EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .entity import PlejdEntity
from .site import PlejdBleConfigEntry, PlejdSite, SignalReading

PARALLEL_UPDATES = 0

# Signaal en laatst gezien lezen we uit het geheugen, dus een minuut is ruim genoeg.
SCAN_INTERVAL = timedelta(minutes=1)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PlejdBleConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Maak de sensoren voor de site, de bewegingssensoren en de apparaten op netstroom."""
    site = entry.runtime_data
    entities: list[SensorEntity] = [PlejdLastCloudSync(site)]
    entities.extend(
        PlejdBatteryLevel(site, device)
        for device in site.devices_of_type(DeviceTypes.PlejdDeviceType.MOTION)
    )
    for device in site.powered_units().values():
        entities.append(PlejdLastSeen(site, device))
        entities.append(PlejdSignalStrength(site, device))
    async_add_entities(entities)


class PlejdLastCloudSync(SensorEntity):
    """Het tijdstip waarop de apparatenlijst voor het laatst uit de cloud kwam."""

    _attr_has_entity_name = True
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False
    _attr_should_poll = False
    _attr_translation_key = "last_cloud_sync"

    def __init__(self, site: PlejdSite) -> None:
        """Koppel de sensor aan de site."""
        self._site = site
        self._attr_unique_id = f"{site.entry.entry_id}:last_cloud_sync"
        self._attr_device_info = site.hub_device_info()

    @property
    def native_value(self) -> datetime | None:
        """Geef het tijdstip, of niets als er nog niets is opgehaald."""
        return self._site.cache_fetched_at


class PlejdBatteryLevel(PlejdEntity, RestoreSensor):
    """Het batterijniveau van een bewegingssensor, zoals het apparaat het meldt.

    pyplejd beschrijft de waarde als "waarschijnlijk 0 tot 255". Omdat dat niet
    is bevestigd, tonen we de ruwe waarde en noemen we het geen percentage.

    Een sensor meldt zijn batterij maar zelden. Daarom bewaren we de laatste
    waarde over een herstart heen, en laten we hem ook zien als het mesh even
    niet verbonden is.
    """

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_translation_key = "battery_level"

    def __init__(self, site: PlejdSite, device: Any) -> None:
        """Begin zonder waarde; die komt pas als de sensor iets meldt."""
        super().__init__(site, device)
        self._attr_unique_id = f"{self._attr_unique_id}:battery"
        self._battery: int | None = None

    @property
    def available(self) -> bool:
        """Toon het laatst bekende niveau, ook zonder Bluetooth-verbinding."""
        return True

    @property
    def native_value(self) -> int | None:
        """Geef het laatst gemelde niveau."""
        return self._battery

    async def async_added_to_hass(self) -> None:
        """Herstel het laatste niveau en luister daarna naar de sensor."""
        last = await self.async_get_last_sensor_data()
        if last is not None and last.native_value is not None:
            self._battery = int(last.native_value)
        await super().async_added_to_hass()

    @callback
    def _handle_device_update(self, data: dict[str, Any]) -> None:
        """Onthoud het niveau zodra de sensor het meldt."""
        if (battery := data.get("battery")) is not None:
            self._battery = battery


class PlejdSignalSensor(SensorEntity):
    """Basis voor sensoren over wat we zelf van een apparaat op netstroom ontvangen."""

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False
    _attr_should_poll = True
    _key: str

    def __init__(self, site: PlejdSite, device: Any) -> None:
        """Koppel de sensor aan het apparaat."""
        self._site = site
        self._address = device.ble_mac.upper()
        self._attr_unique_id = f"{':'.join(device.identifier)}:{self._key}"
        self._attr_device_info = site.entity_device_info(device)

    @property
    def reading(self) -> SignalReading | None:
        """Geef de laatste meting van dit apparaat."""
        return self._site.signal.get(self._address)


class PlejdLastSeen(PlejdSignalSensor):
    """Het tijdstip waarop we het apparaat voor het laatst hoorden."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_translation_key = "last_seen"
    _key = "last_seen"

    @property
    def native_value(self) -> datetime | None:
        """Geef het tijdstip, of niets als we het apparaat nog niet hoorden."""
        return reading.seen_at if (reading := self.reading) else None


class PlejdSignalStrength(PlejdSignalSensor):
    """De signaalsterkte van het apparaat, bij de laatste keer dat we het hoorden."""

    _attr_device_class = SensorDeviceClass.SIGNAL_STRENGTH
    _attr_native_unit_of_measurement = SIGNAL_STRENGTH_DECIBELS_MILLIWATT
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_translation_key = "signal_strength"
    _key = "signal_strength"

    @property
    def native_value(self) -> int | None:
        """Geef de signaalsterkte, of niets als we het apparaat nog niet hoorden."""
        return reading.rssi if (reading := self.reading) else None
