"""Constanten voor Plejd BLE."""

from datetime import timedelta

DOMAIN = "plejd_ble"
MANUFACTURER = "Plejd"

CONF_SITE_ID = "site_id"
CONF_SITE_TITLE = "site_title"

# De cloud van Plejd gebruiken we zuinig: de sitegegevens worden lokaal bewaard
# en pas na deze tijd opnieuw opgehaald.
CLOUD_CACHE_MAX_AGE = timedelta(days=7)
CACHE_STORE_VERSION = 1

# Unieke ID van een Bluetooth-ontdekking, zodat er maar één ontdekking tegelijk loopt.
DISCOVERY_UNIQUE_ID = DOMAIN

# Hoe vaak we controleren of de klok van het mesh nog klopt.
TIME_SYNC_INTERVAL = timedelta(hours=1)
