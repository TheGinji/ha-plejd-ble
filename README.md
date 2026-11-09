# Plejd BLE (revised)

[![HACS: aangepaste repository](https://img.shields.io/badge/HACS-aangepaste%20repository-orange.svg)](https://hacs.xyz/docs/faq/custom_repositories/)
[![Home Assistant: getest op 2026.10 en 2026.11](https://img.shields.io/badge/Home%20Assistant-getest%20op%202026.10%20en%202026.11-41BDF5.svg)](https://www.home-assistant.io/)
[![Release](https://img.shields.io/github/v/release/TheGinji/ha-plejd-ble?include_prereleases)](https://github.com/TheGinji/ha-plejd-ble/releases)
[![Tests](https://github.com/TheGinji/ha-plejd-ble/actions/workflows/tests.yaml/badge.svg)](https://github.com/TheGinji/ha-plejd-ble/actions/workflows/tests.yaml)
[![Validate](https://github.com/TheGinji/ha-plejd-ble/actions/workflows/validate.yaml/badge.svg)](https://github.com/TheGinji/ha-plejd-ble/actions/workflows/validate.yaml)
[![Licentie: MIT](https://img.shields.io/github/license/TheGinji/ha-plejd-ble)](LICENSE)
[![Sterren](https://img.shields.io/github/stars/TheGinji/ha-plejd-ble?style=social)](https://github.com/TheGinji/ha-plejd-ble/stargazers)
[![Ko-fi](https://img.shields.io/badge/Ko--fi-steun%20de%20maker-FF5E5B?logo=ko-fi&logoColor=white)](https://ko-fi.com/theginji)

Home Assistant-integratie voor Plejd-verlichting via Bluetooth (BLE), gebouwd op [pyplejd](https://github.com/thomasloven/pyplejd). Je krijgt je lampen, relais, knoppen en bewegingssensoren in Home Assistant, zonder een berg extra entiteiten.

In Home Assistant en HACS heet deze integratie **Plejd BLE (revised)**. De toevoeging is er om hem te onderscheiden van [hass-plejd](https://github.com/thomasloven/hass-plejd), die zichzelf "Plejd BLE" noemt. Het is een andere integratie, geen nieuwere versie van die van Thomas Lovén.

> **Onofficieel.** Dit project is niet gemaakt, goedgekeurd of ondersteund door Plejd. Plejd is een merk van Plejd AB.
>
> **Testversie.** Het is getest met geautomatiseerde tests en op één echte installatie, maar nog niet op veel verschillende. Zie [Kwaliteit](#kwaliteit).

*English summary: Home Assistant integration for Plejd lighting over Bluetooth, built on pyplejd. It creates only lights, switches, scenes, button events and motion sensors, plus a few diagnostic entities: a refresh button, a Bluetooth connection sensor and a battery level for motion sensors. Per-device signal and last-seen sensors exist but are off by default. Unofficial, and tested with automated tests and on one real installation so far. It is a different integration than hass-plejd and the two cannot run at the same time.*

## Is dit iets voor jou?

Er bestaat al een bekende Plejd-integratie: [hass-plejd](https://github.com/thomasloven/hass-plejd). Die is ouder en breder: volgens zijn README ondersteunt hij meer apparaten, zoals thermostaten. Kies hem als je dat nodig hebt.

Plejd BLE is voor jou als je vooral lampen, dimmers, relais, knoppen en bewegingssensoren hebt en een opgeruimde lijst met entiteiten wilt.

Een voorbeeld, gemeten door de maker op één installatie met 31 apparaten, zonder Bluetooth-verbinding (het gaat dus om aantallen, niet om werking): hass-plejd had daar 225 actieve entiteiten. Dat zijn 18 lampen, 62 knop-events, 17 schakelaars voor de keuze van de Bluetooth-ingang, 62 binaire sensoren, 60 sensoren, 2 scènes en 4 scène-events. De binaire sensoren en sensoren zijn vooral diagnose, zoals verbinding, signaalsterkte en "laatst gezien". Plejd BLE (versie 0.2.2, nog zonder scènes) had op dezelfde installatie 86 actieve entiteiten: de 18 lampen, de 62 knop-events, 2 bewegingssensoren en een paar diagnose-entiteiten (een verversknop, een verbindingssensor en het batterijniveau van de bewegingssensoren). Laatst gezien en signaalsterkte per apparaat bestaan ook, maar staan uit totdat je ze nodig hebt. Met alle diagnose aan zijn het er 121. Sinds versie 0.2.3 komen daar de zichtbare Plejd-scènes bij. De keuze van de Bluetooth-ingang zit in de opties in plaats van in losse schakelaars.

Ze kunnen **niet tegelijk** actief zijn, want een Plejd-apparaat houdt maar één Bluetooth-verbinding tegelijk vast.

## Installatie

Plejd BLE staat nog niet in de standaardlijst van HACS. Voeg hem toe als aangepaste repository:

1. Open HACS, tik op de drie puntjes en kies **Aangepaste repositories**.
2. Plak `https://github.com/TheGinji/ha-plejd-ble`, kies de categorie **Integratie** en voeg toe.
3. Zoek **Plejd BLE (revised)** in HACS en download hem.
4. Start Home Assistant opnieuw.

Je hebt nodig:
- Een Bluetooth-adapter in Home Assistant, of een [ESPHome Bluetooth-proxy](https://esphome.io/components/bluetooth_proxy.html) binnen bereik van je Plejd-apparaten.
- Een account van de Plejd-app.

Vereist Home Assistant 2026.10 of nieuwer. HACS controleert dat bij het installeren. Getest met 2026.10 en 2026.11.

Talen: Nederlands en Engels. Er zijn ook Duitse en Franse teksten, maar die zijn met hulp van Claude vertaald en niet door een moedertaalspreker nagelezen.

## Instellen

1. Ga naar **Instellingen → Apparaten en diensten → Integratie toevoegen** en kies **Plejd BLE (revised)**. In de lijst staan twee integraties met de naam Plejd BLE. Die van ons heeft een lamp als icoon.
2. Log in met je account van de Plejd-app. Heb je meerdere sites, kies er dan één.
3. Klaar. Je apparaten verschijnen met de naam en de kamer uit de Plejd-app.

**Opties.** Via de drie puntjes bij de integratie, onder **Configureren**, kies je welke apparaten op netstroom als Bluetooth-ingang mogen dienen. Haal een apparaat weg als het Bluetooth-signaal daar zwak of onstabiel is. Er moet er minstens één overblijven.

Achter elk apparaat staat de signaalsterkte die Home Assistant op dat moment van het apparaat ontvangt, gemiddeld over de laatste tien metingen, ongeveer de laatste tien minuten. 🟢 is goed (-65 dBm of beter), 🟠 is matig (tot -80 dBm), 🔴 is slecht (zwakker dan -80 dBm) en ⚪ betekent dat er geen recente meting is. Dat zijn vuistregels voor Bluetooth, geen waarden van Plejd. Het gaat om wat jouw Bluetooth-adapter of -proxy hoort, niet om wat de apparaten onderling hebben.

Je wachtwoord wordt in Home Assistant bewaard. De Plejd-cloud wordt alleen gebruikt om je apparatenlijst en de Bluetooth-sleutels op te halen. Bij een herstart van Home Assistant gebruikt de integratie de bewaarde lijst, als die hoogstens zeven dagen oud is. Laad je de integratie zelf opnieuw, of tik je op **Apparatenlijst verversen**, dan wordt de lijst vers opgehaald. De bediening zelf loopt altijd via Bluetooth.

## Wat je krijgt

| Wat | In Home Assistant |
| --- | --- |
| Lamp of dimmer | `light`, met helderheid en, als de lamp het kan, kleurtemperatuur. De laatst bekende kleurtemperatuur blijft bewaard na een herstart |
| Relais | `switch` |
| Scène | `scene`, activeert een scène uit de Plejd-app. Verborgen scènes worden overgeslagen |
| Knop op een paneel | `event` per knop, met `press` en `release` |
| Bewegingssensor | `binary_sensor`, met het lichtniveau als extra gegeven |
| Apparatenlijst verversen | `button`, haalt de lijst opnieuw uit de Plejd-cloud |
| Verbinding met het mesh | `binary_sensor`, diagnostisch. Laat ook zien via welk apparaat je verbonden bent (`connected_via`) |
| Verbonden via | `sensor`, diagnostisch. De naam van het apparaat waarlangs je nu met het mesh verbonden bent, of onbekend zonder verbinding |
| Batterijniveau | `sensor` bij bewegingssensoren, diagnostisch. De ruwe waarde van het apparaat, geen percentage. De laatste waarde blijft bewaard, ook na een herstart en zonder verbinding |
| Laatste cloud-synchronisatie | `sensor`, diagnostisch en standaard uit |
| Laatst gezien en signaalsterkte | `sensor`, twee per apparaat op netstroom, diagnostisch en standaard uit |

Namen komen uit de Plejd-app. Heeft een apparaat daar geen naam, dan krijgt het de productnaam van Plejd, bijvoorbeeld "Wireless push button". Van een model waarvan we de productnaam niet kennen, blijft het modelnummer over. Dezelfde naam in dezelfde kamer wordt genummerd. De kamer zet Home Assistant zelf voor de entiteit-ID, bijvoorbeeld `light.slaapkamer_1_plafondlicht`.

Apparaten die Plejd als verborgen voor integraties markeert, worden overgeslagen.

Een scène activeren is één bericht aan het mesh, in plaats van één bericht per lamp. Wil je meerdere lampen zo gelijk mogelijk laten schakelen, maak dan in de Plejd-app een scène en gebruik die. Wat de scène doet, stel je daar in. Wordt een scène geactiveerd door een schakelaar, de Plejd-app of een schema, dan zet Plejd BLE dat in het attribuut `last_triggered` van de scène. Een automatisering kan daarop reageren met een statustrigger op dat attribuut:

```yaml
triggers:
  - trigger: state
    entity_id: scene.avond_schakelaars
    attribute: last_triggered
```

Dat gebeurt ook als Home Assistant zelf de scène activeert. Laat een automatisering dus niet dezelfde scène activeren waarop hij triggert, anders loopt hij vast in een lus. Een wijziging van alleen een attribuut komt niet in het logboek of de historie van de scène.

Bedien je een lamp of een relais, dan toont Home Assistant direct de nieuwe stand. Een Plejd-apparaat meldt zijn stand zelf pas na ongeveer een seconde terug. Zodra het apparaat de nieuwe stand meldt, telt weer alleen wat het apparaat meldt. Komt er binnen vijf seconden geen melding, dan valt de tegel terug op de laatst gemelde stand. De kleurtemperatuur wordt nooit aangenomen: die zie je pas als het apparaat hem meldt.

Aan of uit en de helderheid vraagt Plejd BLE bij elke verbinding op. De kleurtemperatuur meldt Plejd alleen als hij verandert. Daarom bewaart Plejd BLE de laatst bekende waarde, ook als de lamp uit staat. Is de kleur in de tussentijd in de Plejd-app veranderd, dan klopt de waarde pas weer na de volgende wijziging.

De signaalsterkte en het laatst-gezien-tijdstip meet Plejd BLE zelf, één keer per minuut, bij elk apparaat op netstroom. Home Assistant geeft een bericht dat gelijk is aan het vorige niet door en Plejd-apparaten sturen steeds hetzelfde, daarom vraagt Plejd BLE elke minuut om het volgende bericht. Laatst gezien is dus tot op de minuut nauwkeurig. Dat is bewust niet de waarde van pyplejd: die bewaart de sterkste waarde die ooit is gezien en zegt dus niets over nu. Apparaten op batterij melden zich zelden, dus daar is dit niet voor bedoeld. Het batterijniveau tonen we ruw, want pyplejd weet zelf niet zeker of de schaal 0 tot 255 is. Een sensor meldt zijn batterij zelden, dus de laatste waarde blijft staan tot er een nieuwe komt. Na de hardwaretest kijken we of er een percentage van te maken is.

## Problemen oplossen

**Alles is "niet beschikbaar".** Er is geen Bluetooth-verbinding met je Plejd-mesh. Controleer of de adapter of proxy binnen bereik is van een Plejd-apparaat dat op netstroom werkt. Heb je maar één zo'n apparaat, dan kan Home Assistant volgens de README van hass-plejd niet tegelijk met de Plejd-app of een GWY-01 verbinden.

**Een nieuwe of hernoemde lamp of scène ontbreekt.** Je hebt een lamp of scène in de Plejd-app toegevoegd of gewijzigd, maar Home Assistant gebruikte de bewaarde lijst. Tik op **Apparatenlijst verversen**, of laad de integratie opnieuw via de drie puntjes bij de integratie. Een herstart van Home Assistant is daarvoor niet genoeg. Een scène die in de Plejd-app als verborgen is gemarkeerd, verschijnt niet in Home Assistant.

**Melding "Plejd-cloud niet bereikbaar".** De apparatenlijst kon al meer dan zeven dagen niet worden ververst. De integratie blijft werken met de bewaarde lijst, maar nieuwe of hernoemde apparaten verschijnen pas als de cloud weer bereikbaar is. Je kunt het opnieuw proberen met de knop **Apparatenlijst verversen**.

**Waarlangs ben ik verbonden?** Kijk bij de sensor **Verbonden via** onder het apparaat Plejd BLE, bij Diagnostiek. Die toont de naam van het apparaat waarlangs Home Assistant op dat moment met het mesh verbonden is. Staat de verbindingssensor op uit, dan is er geen verbinding. Zie ook de lijst met apparaten en tijdstippen in de diagnostische gegevens.

**Na een herstart werkt niets.** Lukt de eerste verbinding niet, dan probeert Plejd BLE het na 10, 30, 60 en 120 seconden opnieuw, en daarna elke paar minuten. Na twee mislukte pogingen staat er één waarschuwing in het logboek, met het aantal apparaten dat Home Assistant ziet. Hoort Home Assistant er geen enkel apparaat, dan zit het probleem bij de Bluetooth-adapter of -proxy.

Staat een verbinding open maar antwoordt hij niet meer, dan wordt hij verbroken en opnieuw gemaakt, met een waarschuwing in het logboek.

Op de installatie van de maker gaven opdrachten na een herstart met pyplejd 0.22.0 soms geen effect op lampen die niet de gateway waren, tot de integratie werd herladen. Met pyplejd 0.22.1 werkte het na twee herstarts, via twee verschillende apparaten, direct. Daarom gebruikt Plejd BLE nu pyplejd 0.22.1.

**De inlog wordt geweigerd.** Home Assistant vraagt dan zelf om opnieuw in te loggen. Je kunt de inlog ook wijzigen via de drie puntjes bij de integratie, onder **Opnieuw configureren**.

**Een knop of lamp doet niets.** Controleer eerst of het werkt in de Plejd-app op je telefoon, via Bluetooth, in de buurt van de lampen. Werkt het daar niet, dan zit het probleem niet in deze integratie.

**Een fout melden.** Gebruik de [formulieren](https://github.com/TheGinji/ha-plejd-ble/issues/new/choose). Voeg het bestand toe via **Diagnostische gegevens downloaden** bij de integratie. Dat bevat geen namen, adressen, wachtwoorden of sleutels. Het laat wel zien hoeveel opdrachten een apparaat bevestigde en hoe lang dat duurde. Meer logboek krijg je zo:

```yaml
logger:
  logs:
    custom_components.plejd_ble: debug
    pyplejd: debug
```

Haal wachtwoorden, e-mailadressen, adressen en Bluetooth-adressen uit alles wat je deelt.

## Beperkingen

- Alleen lampen, dimmers, relais, scènes, knoppen en bewegingssensoren. Thermostaten, jaloezieën en de draaiknop worden niet ondersteund. Scènes kun je alleen activeren, aanmaken of wijzigen doe je in de Plejd-app.
- Alleen Bluetooth. Er is geen terugval via de Plejd-cloud: de cloud wordt niet gebruikt om lampen te bedienen.
- De integratie gebruikt de cloud-API die ook de Plejd-app gebruikt. We weten niet of Plejd dat officieel ondersteunt.
- Niet tegelijk met hass-plejd.
- Er is geen beschikbaarheid per apparaat. Valt de verbinding met het mesh weg, dan worden alle entiteiten tegelijk niet beschikbaar. Wie dan precies niet bereikbaar is, zie je aan de sensoren voor laatst gezien.
- Twee opdrachten vlak na elkaar aan dezelfde lamp, bijvoorbeeld aan en uit binnen een paar seconden, kunnen de tweede kwijtraken. De tegel valt dan na 5 seconden terug op de echte stand.
- Alles is gebouwd op pyplejd, dat door één persoon wordt onderhouden. We gebruiken één vaste versie en een test controleert of die nog past.
- Getest op één installatie, zie [Kwaliteit](#kwaliteit).

## Verwijderen

Verwijder de integratie via **Instellingen → Apparaten en diensten**. De lokaal bewaarde apparatenlijst, met de sleutels, wordt dan ook gewist, net als een eventuele melding over de cloud. Wil je Plejd BLE helemaal weghalen, verwijder hem dan ook in HACS.

## Kwaliteit

Custom integrations hebben geen officiële kwaliteitsscore van Home Assistant. Dit hebben we zelf getoetst:

- Meer dan 60 geautomatiseerde tests, met een dekking van minstens 95%. De workflow laat een run falen onder die grens.
- De tests draaien bij elke wijziging en elke week op de nieuwste Home Assistant, en ook op de oudste ondersteunde versie. Een extra proef op de komende bètaversie waarschuwt eerder voor wijzigingen, maar blokkeert niets.
- [Hassfest](https://developers.home-assistant.io/blog/2020/04/16/hassfest/) en de HACS-controle, zonder uitzonderingen. Beide draaien ook elke week.
- Tests die controleren of de onderdelen van pyplejd die we gebruiken niet veranderen.
- Een proef op één echte installatie, zie hieronder.

### Getest op een echte installatie

De installatie van de maker: 31 apparaten, een Raspberry Pi met ingebouwde Bluetooth, Home Assistant 2026.11 en pyplejd 0.22.1.

- Lampen aan, uit en dimmen vanuit Home Assistant. Het apparaat bevestigt gemiddeld na ongeveer 1,1 seconde.
- De directe tegel na een opdracht.
- Paneelknoppen, bewegingssensoren en scènes, ook als de scène vanaf een schakelaar of de Plejd-app wordt geactiveerd.
- Een herstart van Home Assistant: opdrachten aan lampen die niet de gateway zijn werken direct, zowel via Hal als via Trapkast als Bluetooth-ingang.
- Het wisselen van Bluetooth-ingang in de opties.
- Gelijktijdig gebruik met de Plejd-app en een GWY-01.
- Ruim 20 uur zonder één mislukte keep-alive, ook 's nachts.
- De signaalsensoren en laatst gezien.

**Nog niet getest:** een ESPHome-proxy, plotseling loskoppelen van de adapter, de kleurtemperatuur van lampen die dat kunnen en andere installaties.

## Steun

Dit project is gratis (MIT). Wil je de maker steunen, dan kan dat via [Ko-fi](https://ko-fi.com/theginji).

## Licentie en credits

MIT, zie [LICENSE](LICENSE).

- [pyplejd](https://github.com/thomasloven/pyplejd) en [hass-plejd](https://github.com/thomasloven/hass-plejd) van Thomas Lovén (MIT). Zonder zijn werk was dit er niet.
- De community die het Plejd-protocol heeft ontcijferd, zoals genoemd in de README van hass-plejd.
- Het icoon is een eigen ontwerp. Alleen de kleur lijkt op die van Plejd.
- Gemaakt met hulp van Claude (Anthropic).
