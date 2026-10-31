# Plejd BLE

[![HACS: aangepaste repository](https://img.shields.io/badge/HACS-aangepaste%20repository-orange.svg)](https://hacs.xyz/docs/faq/custom_repositories/)
[![Home Assistant: getest op 2026.10](https://img.shields.io/badge/Home%20Assistant-getest%20op%202026.10-41BDF5.svg)](https://www.home-assistant.io/)
[![Release](https://img.shields.io/github/v/release/TheGinji/ha-plejd-ble?include_prereleases)](https://github.com/TheGinji/ha-plejd-ble/releases)
[![Tests](https://github.com/TheGinji/ha-plejd-ble/actions/workflows/tests.yaml/badge.svg)](https://github.com/TheGinji/ha-plejd-ble/actions/workflows/tests.yaml)
[![Validate](https://github.com/TheGinji/ha-plejd-ble/actions/workflows/validate.yaml/badge.svg)](https://github.com/TheGinji/ha-plejd-ble/actions/workflows/validate.yaml)
[![Licentie: MIT](https://img.shields.io/github/license/TheGinji/ha-plejd-ble)](LICENSE)
[![Sterren](https://img.shields.io/github/stars/TheGinji/ha-plejd-ble?style=social)](https://github.com/TheGinji/ha-plejd-ble/stargazers)
[![Ko-fi](https://img.shields.io/badge/Ko--fi-steun%20de%20maker-FF5E5B?logo=ko-fi&logoColor=white)](https://ko-fi.com/theginji)

Home Assistant-integratie voor Plejd-verlichting via Bluetooth (BLE), gebouwd op [pyplejd](https://github.com/thomasloven/pyplejd). Je krijgt je lampen, relais, knoppen en bewegingssensoren in Home Assistant, zonder een berg extra entiteiten.

> **Onofficieel.** Dit project is niet gemaakt, goedgekeurd of ondersteund door Plejd. Plejd is een merk van Plejd AB.
>
> **Testversie.** Het is getest met geautomatiseerde tests, maar nog niet op echte Plejd-apparaten. Zie [Kwaliteit](#kwaliteit).

*English summary: Home Assistant integration for Plejd lighting over Bluetooth, built on pyplejd. It creates only lights, switches, button events and motion sensors, plus one refresh button and one optional diagnostic sensor that is off by default. There are no diagnostic entities per device. Unofficial, and tested with automated tests only so far, not yet on real hardware. It is a different integration than hass-plejd and the two cannot run at the same time.*

## Is dit iets voor jou?

Er bestaat al een bekende Plejd-integratie: [hass-plejd](https://github.com/thomasloven/hass-plejd). Die is ouder en breder: volgens zijn README ondersteunt hij meer apparaten, zoals scènes en thermostaten. Kies hem als je dat nodig hebt.

Plejd BLE is voor jou als je vooral lampen, dimmers, relais, knoppen en bewegingssensoren hebt en een opgeruimde lijst met entiteiten wilt.

Een voorbeeld, gemeten door de maker op één installatie met 27 apparaten: hass-plejd maakte daar 191 entiteiten aan. Daarvan waren er 74 lampen, knoppen en bewegingssensoren. De overige 117 waren diagnose- of configuratie-entiteiten, zoals signaalsterkte en "laatst gezien". Plejd BLE maakt die per apparaat niet aan. Er komen alleen een verversknop en een diagnosesensor bij, en die sensor staat standaard uit. Hoeveel entiteiten het op echte apparaten worden, meten we pas bij de eerste test op hardware.

Ze kunnen **niet tegelijk** actief zijn, want een Plejd-apparaat houdt maar één Bluetooth-verbinding tegelijk vast.

## Installatie

Plejd BLE staat nog niet in de standaardlijst van HACS. Voeg hem toe als aangepaste repository:

1. Open HACS, tik op de drie puntjes en kies **Aangepaste repositories**.
2. Plak `https://github.com/TheGinji/ha-plejd-ble`, kies de categorie **Integratie** en voeg toe.
3. Zoek **Plejd BLE** in HACS en download hem.
4. Start Home Assistant opnieuw.

Je hebt nodig:
- Een Bluetooth-adapter in Home Assistant, of een [ESPHome Bluetooth-proxy](https://esphome.io/components/bluetooth_proxy.html) binnen bereik van je Plejd-apparaten.
- Een account van de Plejd-app.

Getest is alleen met Home Assistant 2026.10. Oudere versies zijn niet getest.

Talen: Nederlands en Engels. Er zijn ook Duitse en Franse teksten, maar die zijn met hulp van Claude vertaald en niet door een moedertaalspreker nagelezen.

## Instellen

1. Ga naar **Instellingen → Apparaten en diensten → Integratie toevoegen** en kies **Plejd BLE**.
2. Log in met je account van de Plejd-app. Heb je meerdere sites, kies er dan één.
3. Klaar. Je apparaten verschijnen met de naam en de kamer uit de Plejd-app.

**Opties.** Via de drie puntjes bij de integratie, onder **Configureren**, kies je welke apparaten op netstroom als Bluetooth-ingang mogen dienen. Haal een apparaat weg als het Bluetooth-signaal daar zwak of onstabiel is. Er moet er minstens één overblijven.

Je wachtwoord wordt in Home Assistant bewaard. De Plejd-cloud wordt alleen gebruikt om je apparatenlijst en de Bluetooth-sleutels op te halen, en die gegevens blijven zeven dagen lokaal bewaard. De bediening zelf loopt altijd via Bluetooth.

## Wat je krijgt

| Wat | In Home Assistant |
| --- | --- |
| Lamp of dimmer | `light`, met helderheid en, als de lamp het kan, kleurtemperatuur |
| Relais | `switch` |
| Knop op een paneel | `event` per knop, met `press` en `release` |
| Bewegingssensor | `binary_sensor`, met batterij en lichtniveau als extra gegevens |
| Apparatenlijst verversen | `button`, haalt de lijst opnieuw uit de Plejd-cloud |
| Laatste cloud-synchronisatie | `sensor`, diagnostisch en standaard uit |

Namen komen uit de Plejd-app. Heeft een apparaat daar geen naam, dan krijgt het de naam van het model, bijvoorbeeld `WPH-01-LC`. Dezelfde naam in dezelfde kamer wordt genummerd. De kamer zet Home Assistant zelf voor de entiteit-ID, bijvoorbeeld `light.slaapkamer_1_plafondlicht`.

Apparaten die Plejd als verborgen voor integraties markeert, worden overgeslagen.

## Problemen oplossen

**Alles is "niet beschikbaar".** Er is geen Bluetooth-verbinding met je Plejd-mesh. Controleer of de adapter of proxy binnen bereik is van een Plejd-apparaat dat op netstroom werkt. Heb je maar één zo'n apparaat, dan kan Home Assistant volgens de README van hass-plejd niet tegelijk met de Plejd-app of een GWY-01 verbinden.

**Melding "Plejd-cloud niet bereikbaar".** De apparatenlijst kon al meer dan zeven dagen niet worden ververst. De integratie blijft werken met de bewaarde lijst, maar nieuwe of hernoemde apparaten verschijnen pas als de cloud weer bereikbaar is. Je kunt het proberen met de knop **Apparatenlijst verversen**.

**De inlog wordt geweigerd.** Home Assistant vraagt dan zelf om opnieuw in te loggen. Je kunt de inlog ook wijzigen via de drie puntjes bij de integratie, onder **Opnieuw configureren**.

**Een knop of lamp doet niets.** Controleer eerst of het werkt in de Plejd-app op je telefoon, via Bluetooth, in de buurt van de lampen. Werkt het daar niet, dan zit het probleem niet in deze integratie.

**Een fout melden.** Gebruik de [formulieren](https://github.com/TheGinji/ha-plejd-ble/issues/new/choose). Voeg het bestand toe via **Diagnostische gegevens downloaden** bij de integratie. Dat bevat geen namen, adressen, wachtwoorden of sleutels. Meer logboek krijg je zo:

```yaml
logger:
  logs:
    custom_components.plejd_ble: debug
    pyplejd: debug
```

Haal wachtwoorden, e-mailadressen, adressen en Bluetooth-adressen uit alles wat je deelt.

## Beperkingen

- Alleen lampen, dimmers, relais, knoppen en bewegingssensoren. Scènes, thermostaten, jaloezieën en de draaiknop worden niet ondersteund.
- Alleen Bluetooth. Er is geen terugval via de Plejd-cloud: de cloud wordt niet gebruikt om lampen te bedienen.
- De integratie gebruikt de cloud-API die ook de Plejd-app gebruikt. We weten niet of Plejd dat officieel ondersteunt.
- Niet tegelijk met hass-plejd.
- Alles is gebouwd op pyplejd, dat door één persoon wordt onderhouden. We gebruiken één vaste versie en een test controleert of die nog past.
- Nog niet getest op echte apparaten.

## Verwijderen

Verwijder de integratie via **Instellingen → Apparaten en diensten**. De lokaal bewaarde apparatenlijst, met de sleutels, wordt dan ook gewist, net als een eventuele melding over de cloud. Wil je Plejd BLE helemaal weghalen, verwijder hem dan ook in HACS.

## Kwaliteit

Custom integrations hebben geen officiële kwaliteitsscore van Home Assistant. Dit hebben we zelf getoetst:

- Meer dan 60 geautomatiseerde tests, met een dekking van minstens 95%. De workflow laat een run falen onder die grens.
- [Hassfest](https://developers.home-assistant.io/blog/2020/04/16/hassfest/) en de HACS-controle, zonder uitzonderingen. Beide draaien ook elke week.
- Tests die controleren of de onderdelen van pyplejd die we gebruiken niet veranderen.

Wat we **niet** getest hebben: echte Bluetooth, echte Plejd-apparaten en Home Assistant-versies ouder dan 2026.10.

## Steun

Dit project is gratis (MIT). Wil je de maker steunen, dan kan dat via [Ko-fi](https://ko-fi.com/theginji).

## Licentie en credits

MIT, zie [LICENSE](LICENSE).

- [pyplejd](https://github.com/thomasloven/pyplejd) en [hass-plejd](https://github.com/thomasloven/hass-plejd) van Thomas Lovén (MIT). Zonder zijn werk was dit er niet.
- De community die het Plejd-protocol heeft ontcijferd, zoals genoemd in de README van hass-plejd.
- Het icoon is een eigen ontwerp. Alleen de kleur lijkt op die van Plejd.
- Gemaakt met hulp van Claude (Anthropic).
