# Plejd BLE

Home Assistant-integratie voor Plejd-verlichting via Bluetooth (BLE), gebouwd op [pyplejd](https://github.com/thomasloven/pyplejd).

> **Status: werk in uitvoering.** Er is nog geen werkende versie en niets is nog getest op echte hardware. Installeer dit nog niet.

## Doel

Een eigen Plejd-integratie met minder overbodige entiteiten en rustiger logs. Dat zijn doelen, geen beloftes: we meten het pas als er een werkende versie is.

## Let op

- Dit is een **andere integratie dan [hass-plejd](https://github.com/thomasloven/hass-plejd)**, ook al lijkt de naam erop. De twee kunnen niet tegelijk actief zijn, want een Plejd-apparaat houdt maar één Bluetooth-verbinding tegelijk vast.
- De integratie gebruikt de cloud-API die ook de Plejd-app gebruikt om je apparaten en sleutels op te halen. We weten niet of Plejd dit officieel ondersteunt.
- Bediening gaat via Bluetooth. Bediening via de cloud wordt niet ondersteund.

## English summary

Home Assistant integration for Plejd lighting over Bluetooth, built on pyplejd. Work in progress: not usable yet and not tested on real hardware. This is a different integration than hass-plejd and the two cannot run at the same time.

## Credits

- [pyplejd](https://github.com/thomasloven/pyplejd) en [hass-plejd](https://github.com/thomasloven/hass-plejd) van Thomas Lovén (MIT).
- De community die het Plejd-protocol heeft ontcijferd, zoals genoemd in de README van hass-plejd.

## Licentie

MIT, zie [LICENSE](LICENSE).
