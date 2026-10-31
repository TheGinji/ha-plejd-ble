"""Configuratie van Plejd BLE: inloggen, site kiezen, opnieuw inloggen."""

from __future__ import annotations

from collections.abc import Mapping
import logging
from typing import Any

from pyplejd import (
    AuthenticationError,
    ConnectionError as PlejdConnectionError,
    get_sites,
)
import voluptuous as vol

from homeassistant.components import bluetooth
from homeassistant.config_entries import SOURCE_REAUTH, ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.helpers.selector import (
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .const import CONF_SITE_ID, CONF_SITE_TITLE, DISCOVERY_UNIQUE_ID, DOMAIN

_LOGGER = logging.getLogger(__name__)

CREDENTIALS_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): TextSelector(
            TextSelectorConfig(type=TextSelectorType.EMAIL, autocomplete="username")
        ),
        vol.Required(CONF_PASSWORD): TextSelector(
            TextSelectorConfig(
                type=TextSelectorType.PASSWORD, autocomplete="current-password"
            )
        ),
    }
)


class PlejdBleConfigFlow(ConfigFlow, domain=DOMAIN):
    """Configuratiestroom voor Plejd BLE."""

    VERSION = 1

    def __init__(self) -> None:
        """Begin zonder gegevens."""
        self._username = ""
        self._password = ""
        self._sites: dict[str, dict[str, Any]] = {}

    async def async_step_bluetooth(
        self, discovery_info: bluetooth.BluetoothServiceInfoBleak
    ) -> ConfigFlowResult:
        """Verwerk een gevonden Plejd-apparaat."""
        # Meerdere apparaten van hetzelfde mesh melden zich tegelijk;
        # met deze ID blijft er maar één ontdekking over.
        await self.async_set_unique_id(DISCOVERY_UNIQUE_ID)
        if self._async_current_entries():
            return self.async_abort(reason="already_configured")
        return await self.async_step_user()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Vraag de inloggegevens van de Plejd-app."""
        if not bluetooth.async_scanner_count(self.hass, connectable=True):
            return self.async_abort(reason="bluetooth_not_available")

        errors: dict[str, str] = {}
        if user_input is not None:
            self._username = user_input[CONF_USERNAME]
            self._password = user_input[CONF_PASSWORD]
            sites, error = await self._async_get_sites(self._username, self._password)
            if error:
                errors["base"] = error
            elif not sites:
                return self.async_abort(reason="no_sites")
            else:
                self._sites = sites
                if len(sites) == 1:
                    return await self._async_create_entry(next(iter(sites)))
                return await self.async_step_site()

        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(
                CREDENTIALS_SCHEMA, {CONF_USERNAME: self._username}
            ),
            errors=errors,
        )

    async def async_step_site(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Laat de gebruiker een site kiezen als er meer dan één is."""
        if user_input is not None:
            return await self._async_create_entry(user_input[CONF_SITE_ID])

        options = [
            SelectOptionDict(
                value=site_id,
                label=f"{site['title']} ({site['deviceCount']})".strip(),
            )
            for site_id, site in self._sites.items()
        ]
        return self.async_show_form(
            step_id="site",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_SITE_ID): SelectSelector(
                        SelectSelectorConfig(
                            options=options, mode=SelectSelectorMode.LIST
                        )
                    )
                }
            ),
        )

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Vraag opnieuw inloggegevens als de cloud ze niet meer accepteert."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Verwerk de nieuwe inloggegevens."""
        return await self._async_step_credentials("reauth_confirm", user_input)

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Laat de gebruiker de inloggegevens wijzigen."""
        return await self._async_step_credentials("reconfigure", user_input)

    async def _async_step_credentials(
        self, step_id: str, user_input: dict[str, Any] | None
    ) -> ConfigFlowResult:
        """Controleer nieuwe inloggegevens voor een bestaand item."""
        entry = (
            self._get_reauth_entry()
            if self.source == SOURCE_REAUTH
            else self._get_reconfigure_entry()
        )
        errors: dict[str, str] = {}
        if user_input is not None:
            sites, error = await self._async_get_sites(
                user_input[CONF_USERNAME], user_input[CONF_PASSWORD]
            )
            if error:
                errors["base"] = error
            elif entry.data[CONF_SITE_ID] not in sites:
                errors["base"] = "site_not_found"
            else:
                return self.async_update_reload_and_abort(
                    entry,
                    data_updates={
                        CONF_USERNAME: user_input[CONF_USERNAME],
                        CONF_PASSWORD: user_input[CONF_PASSWORD],
                    },
                )

        return self.async_show_form(
            step_id=step_id,
            data_schema=self.add_suggested_values_to_schema(
                CREDENTIALS_SCHEMA, {CONF_USERNAME: entry.data[CONF_USERNAME]}
            ),
            errors=errors,
        )

    async def _async_get_sites(
        self, username: str, password: str
    ) -> tuple[dict[str, dict[str, Any]], str | None]:
        """Log in bij Plejd en geef de sites van dit account, of een foutcode."""
        try:
            sites = await get_sites(username=username, password=password)
        except AuthenticationError:
            return {}, "invalid_auth"
        except PlejdConnectionError:
            return {}, "cannot_connect"
        except Exception:  # noqa: BLE001
            _LOGGER.exception("Onverwachte fout bij het ophalen van de Plejd-sites")
            return {}, "unknown"
        return {site["siteId"]: site for site in sites}, None

    async def _async_create_entry(self, site_id: str) -> ConfigFlowResult:
        """Maak het configuratie-item voor de gekozen site."""
        await self.async_set_unique_id(site_id)
        self._abort_if_unique_id_configured()
        title = self._sites[site_id]["title"]
        return self.async_create_entry(
            title=title or "Plejd",
            data={
                CONF_USERNAME: self._username,
                CONF_PASSWORD: self._password,
                CONF_SITE_ID: site_id,
                CONF_SITE_TITLE: title,
            },
        )
