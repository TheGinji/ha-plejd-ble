"""Constanten voor Plejd BLE."""

from datetime import timedelta
from typing import Final

DOMAIN: Final = "plejd_ble"
MANUFACTURER: Final = "Plejd"

CONF_SITE_ID: Final = "site_id"
CONF_SITE_TITLE: Final = "site_title"

# Opties: apparaten die niet als Bluetooth-ingang mogen dienen, en (alleen in het
# optiesscherm) de apparaten die dat wel mogen.
CONF_BLOCKED_DEVICES: Final = "blocked_devices"
CONF_ALLOWED_DEVICES: Final = "allowed_devices"

# De cloud van Plejd gebruiken we zuinig: de sitegegevens worden lokaal bewaard
# en pas na deze tijd opnieuw opgehaald.
CLOUD_CACHE_MAX_AGE: Final = timedelta(days=7)
CACHE_STORE_VERSION: Final = 1

# Unieke ID van een Bluetooth-ontdekking, zodat er maar één ontdekking tegelijk loopt.
DISCOVERY_UNIQUE_ID: Final = DOMAIN

# Hoe vaak we controleren of de klok van het mesh nog klopt.
TIME_SYNC_INTERVAL: Final = timedelta(hours=1)
