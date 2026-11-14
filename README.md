# Plejd BLE (revised)

[![HACS: Custom repository](https://img.shields.io/badge/HACS-Custom%20repository-orange.svg)](https://hacs.xyz/docs/faq/custom_repositories/)
[![Home Assistant: tested on 2026.10 and 2026.11](https://img.shields.io/badge/Home%20Assistant-tested%20on%202026.10%20and%202026.11-41BDF5.svg)](https://www.home-assistant.io/)
[![Release](https://img.shields.io/github/v/release/TheGinji/ha-plejd-ble?include_prereleases)](https://github.com/TheGinji/ha-plejd-ble/releases)
[![Tests](https://github.com/TheGinji/ha-plejd-ble/actions/workflows/tests.yaml/badge.svg)](https://github.com/TheGinji/ha-plejd-ble/actions/workflows/tests.yaml)
[![Validate](https://github.com/TheGinji/ha-plejd-ble/actions/workflows/validate.yaml/badge.svg)](https://github.com/TheGinji/ha-plejd-ble/actions/workflows/validate.yaml)
[![License: MIT](https://img.shields.io/github/license/TheGinji/ha-plejd-ble)](LICENSE)
[![Stars](https://img.shields.io/github/stars/TheGinji/ha-plejd-ble?style=social)](https://github.com/TheGinji/ha-plejd-ble/stargazers)
[![Ko-fi](https://img.shields.io/badge/Ko--fi-support%20the%20maker-FF5E5B?logo=ko-fi&logoColor=white)](https://ko-fi.com/theginji)

Home Assistant integration for Plejd lighting over Bluetooth (BLE), built on [pyplejd](https://github.com/thomasloven/pyplejd). You get your lights, relays, buttons and motion sensors in Home Assistant, without a pile of extra entities.

In Home Assistant and HACS this integration is called **Plejd BLE (revised)**. The addition is there to tell it apart from [hass-plejd](https://github.com/thomasloven/hass-plejd), which calls itself "Plejd BLE". It is a different integration, not a newer version of the one by Thomas Lovén.

> **Unofficial.** This project is not made, approved or supported by Plejd. Plejd is a trademark of Plejd AB.
>
> **Test version.** It has been tested with automated tests and on one real installation, but not yet on many different ones. See [Quality](#quality).

## Is this for you?

A well-known Plejd integration already exists: [hass-plejd](https://github.com/thomasloven/hass-plejd). It is older and broader: according to its README it supports more devices, such as thermostats. Choose it if you need that.

Plejd BLE is for you if you mostly have lights, dimmers, relays, buttons and motion sensors and want a tidy list of entities.

An example, measured by the maker on one installation with 31 devices, without a Bluetooth connection (so this is about counts, not about behaviour): hass-plejd had 225 active entities there. That is 18 lights, 62 button events, 17 switches for choosing the Bluetooth input, 62 binary sensors, 60 sensors, 2 scenes and 4 scene events. The binary sensors and sensors are mostly diagnostics, such as connection, signal strength and "last seen". Plejd BLE (version 0.2.2, without scenes yet) had 86 active entities on the same installation: the 18 lights, the 62 button events, 2 motion sensors and a few diagnostic entities (a refresh button, a connection sensor and the battery level of the motion sensors). Last seen and signal strength per device exist too, but are off until you need them. With all diagnostics on, that makes 121. Since version 0.2.3 the visible Plejd scenes are added on top. With them, Home Assistant lists 125 entities for the same installation (version 0.2.17). The choice of Bluetooth input lives in the options instead of separate switches.

They **cannot run at the same time**, because a Plejd device holds only one Bluetooth connection at a time.

## Installation

Plejd BLE is not in the default HACS list yet. Add it as a custom repository:

1. Open HACS, tap the three dots and choose **Custom repositories**.
2. Paste `https://github.com/TheGinji/ha-plejd-ble`, choose the category **Integration** and add it.
3. Search for **Plejd BLE (revised)** in HACS and download it.
4. Restart Home Assistant.

You need:
- A Bluetooth adapter in Home Assistant, or an [ESPHome Bluetooth proxy](https://esphome.io/components/bluetooth_proxy.html) within range of your Plejd devices.
- An account for the Plejd app.

Requires Home Assistant 2026.10 or newer. HACS checks this when you install. Tested with 2026.10 and 2026.11.

Languages: Dutch and English. German and French texts are included too, but they were translated with AI and have not been reviewed by a native speaker. Feedback is welcome from anyone who reads and writes these languages.

## Setup

1. Go to **Settings → Devices & services → Add integration** and choose **Plejd BLE (revised)**. The list shows two integrations called Plejd BLE. Ours has a lamp as its icon.
2. Log in with your Plejd app account. If you have several sites, pick one.
3. Done. Your devices appear with the name and room from the Plejd app.

**Options.** Via the three dots next to the integration, under **Configure**, you choose which devices on mains power may serve as the Bluetooth entry point. Remove a device if the Bluetooth signal there is weak or unstable. At least one must remain.

Next to each device you see the signal strength that Home Assistant currently receives from that device, averaged over the last ten measurements, roughly the last ten minutes. 🟢 is good (-65 dBm or better), 🟠 is fair (down to -80 dBm), 🔴 is poor (weaker than -80 dBm) and ⚪ means there is no recent measurement. These are Bluetooth rules of thumb, not Plejd values. They describe what your Bluetooth adapter or proxy hears, not what the devices hear from each other.

Your password is stored in Home Assistant. The Plejd cloud is only used to fetch your device list and the Bluetooth keys. When Home Assistant restarts, the integration uses the stored list, as long as it is at most seven days old. If you reload the integration yourself, or tap **Refresh device list**, the list is fetched fresh. Control itself always goes over Bluetooth.

## What you get

| What | In Home Assistant |
| --- | --- |
| Light or dimmer | `light`, with brightness and, if the light supports it, color temperature. The last known color temperature is kept after a restart |
| Relay | `switch` |
| Scene | `scene`, activates a scene from the Plejd app. Hidden scenes are skipped |
| Button on a panel | `event` per button, with `press` and `release` |
| Motion sensor | `binary_sensor`, with the light level as an extra attribute |
| Refresh device list | `button`, fetches the list from the Plejd cloud again |
| Bluetooth mesh connection | `binary_sensor`, diagnostic. Also shows which device you are connected through (`connected_via`) |
| Connected via | `sensor`, diagnostic. The name of the device you are currently connected to the mesh through, or unknown without a connection |
| Battery level | `sensor` on motion sensors, diagnostic. The raw value from the device, not a percentage. The last value is kept, also after a restart and without a connection |
| Last cloud sync | `sensor`, diagnostic and off by default |
| Last seen and signal strength | `sensor`, two per device on mains power, diagnostic and off by default |

Names come from the Plejd app. If a device has no name there, it gets Plejd's product name, for example "Wireless push button". For a model whose product name we do not know, the model number is used. The same name in the same room is numbered. Home Assistant itself puts the room in front of the entity ID, for example `light.bedroom_1_ceiling_light`.

Devices that Plejd marks as hidden for integrations are skipped.

Activating a scene is one message to the mesh, instead of one message per light. If you want several lights to switch as simultaneously as possible, create a scene in the Plejd app and use that. What the scene does is set up there. If a scene is activated by a switch, the Plejd app or a schedule, Plejd BLE records that in the scene's `last_triggered` attribute. An automation can react to that with a state trigger on that attribute:

```yaml
triggers:
  - trigger: state
    entity_id: scene.evening_switches
    attribute: last_triggered
```

This also happens when Home Assistant itself activates the scene. So do not let an automation activate the same scene it triggers on, or it will loop. A change of only an attribute does not show up in the logbook or history of the scene.

When you control a light or a relay, Home Assistant shows the new state right away. A Plejd device reports its own state back only after about a second. As soon as the device reports the new state, only what the device reports counts again. If no report arrives within five seconds, the tile falls back to the last reported state. Color temperature is never assumed: you see it only once the device reports it.

On/off and brightness are requested by Plejd BLE at every connection. For relays this works since pyplejd 0.22.1; older versions showed relays as off after a restart until their next state change. We have not yet seen this on real hardware, see [Quality](#quality). Plejd only reports color temperature when it changes. That is why Plejd BLE keeps the last known value, even when the light is off. If the color was changed in the Plejd app in the meantime, the value is only correct again after the next change.

Plejd BLE measures signal strength and last-seen time itself, once a minute, for every device on mains power. Home Assistant does not pass on a message that is identical to the previous one, and Plejd devices keep sending the same one, so Plejd BLE asks for the next message every minute. Last seen is therefore accurate to the minute. This is deliberately not the value from pyplejd: that one keeps the strongest value ever seen and so says nothing about now. Battery-powered devices rarely report, so this is not meant for them. The battery level is shown raw, because pyplejd itself is not sure whether the scale is 0 to 255. A sensor rarely reports its battery, so the last value stays until a new one arrives. After the hardware test we will check whether a percentage can be made of it.

## Troubleshooting

**Everything is "unavailable".** There is no Bluetooth connection to your Plejd mesh. Check that the adapter or proxy is within range of a Plejd device that runs on mains power. If you have only one such device, then according to the hass-plejd README Home Assistant cannot connect at the same time as the Plejd app or a GWY-01.

**A new or renamed light or scene is missing.** You added or changed a light or scene in the Plejd app, but Home Assistant used the stored list. Tap **Refresh device list**, or reload the integration via the three dots next to it. A restart of Home Assistant is not enough for this. A scene that is marked as hidden in the Plejd app does not appear in Home Assistant.

**Notice "Plejd cloud is not reachable".** The device list could not be refreshed for more than seven days. The integration keeps working with the stored list, but new or renamed devices only appear once the cloud is reachable again. You can try again with the **Refresh device list** button.

**Notice "No Bluetooth connection to the Plejd mesh".** This appears under Repairs when there has been no connection for five minutes. It disappears by itself as soon as the connection is back. A short interruption does not give a notice, such as the recovery after the device you are connected through drops out, which takes about a minute. If you get the notice, check that the Bluetooth adapter or proxy works and is within range of a Plejd device that runs on mains power.

**Warning "A message from the Plejd mesh could not be processed".** This comes from pyplejd, which cannot handle a message with empty content. Plejd BLE catches it, and only that one message is lost. You see the warning at most once per start. The number and kind of error are in the diagnostics.

**Which device am I connected through?** Look at the **Connected via** sensor under the Plejd BLE device, in the Diagnostic section. It shows the name of the device that Home Assistant is currently connected to the mesh through. If the connection sensor is off, there is no connection. See also the list of devices and times in the diagnostics.

**Nothing works after a restart.** If the first connection fails, Plejd BLE tries again after 10, 30, 60 and 120 seconds, and after that every few minutes. After two failed attempts there is one warning in the log, with the number of devices that Home Assistant sees. If Home Assistant does not hear a single device, the problem is with the Bluetooth adapter or proxy.

If a connection is open but no longer answers, it is dropped and made again, with a warning in the log.

On the maker's installation, commands after a restart with pyplejd 0.22.0 sometimes had no effect on lights that were not the gateway, until the integration was reloaded. With pyplejd 0.22.1 it worked straight away after two restarts, through two different devices. That is why Plejd BLE now uses pyplejd 0.22.1.

**The login is rejected.** Home Assistant then asks you to log in again. You can also change the login via the three dots next to the integration, under **Reconfigure**.

**A button or light does nothing.** First check whether it works in the Plejd app on your phone, over Bluetooth, near the lights. If it does not work there, the problem is not in this integration.

**Reporting a bug.** Use the [forms](https://github.com/TheGinji/ha-plejd-ble/issues/new/choose). Attach the file from **Download diagnostics** on the integration. It contains no names, addresses, passwords or keys. It does show how many commands a device confirmed and how long that took. You get more log output like this:

```yaml
logger:
  logs:
    custom_components.plejd_ble: debug
    pyplejd: debug
```

Remove passwords, email addresses, addresses and Bluetooth addresses from anything you share.

## Limitations

- Only lights, dimmers, relays, scenes, buttons and motion sensors. Thermostats, blinds and the rotary dial are not supported. Scenes can only be activated; creating or changing them is done in the Plejd app.
- Bluetooth only. There is no fallback through the Plejd cloud: the cloud is not used to control lights.
- The integration uses the cloud API that the Plejd app also uses. We do not know whether Plejd officially supports that.
- Not at the same time as hass-plejd.
- If the device you are connected through drops out, it takes about a minute before Home Assistant is connected through another device. pyplejd first tries the device that is no longer reachable, ten times. During that minute the entities are unavailable. Your Plejd switches keep working.
- There is no availability per device. If the connection to the mesh drops, all entities become unavailable at once. You can see who exactly is unreachable from the last-seen sensors.
- Two commands to the same light right after each other, for example on and off within a few seconds, can lose the second one. The tile then falls back to the real state after 5 seconds.
- Everything is built on pyplejd, which is maintained by one person. We use one fixed version, and a test checks that it still fits.
- Tested on one installation, see [Quality](#quality).

## Removal

Remove the integration via **Settings → Devices & services**. The locally stored device list, with the keys, is then wiped too, as is any notice about the cloud. If you want to remove Plejd BLE completely, also remove it in HACS.

## Quality

Custom integrations have no official quality score from Home Assistant. This is what we checked ourselves:

- More than 60 automated tests, with at least 95% coverage. The workflow fails a run below that limit.
- The tests run on every change and every week on the newest Home Assistant, and also on the oldest supported version. An extra check on the upcoming beta version warns earlier about changes, but blocks nothing.
- [Hassfest](https://developers.home-assistant.io/blog/2020/04/16/hassfest/) and the HACS check, without exceptions. Both also run every week.
- Tests that check that the parts of pyplejd we use do not change.
- A trial on one real installation, see below.

### Tested on a real installation

The maker's installation: 31 devices, a Raspberry Pi with built-in Bluetooth, Home Assistant 2026.11 and pyplejd 0.22.1.

- Lights on, off and dimming from Home Assistant. The device confirms after about 1.1 seconds on average.
- The immediate tile after a command.
- Panel buttons, motion sensors and scenes, also when the scene is activated from a switch or the Plejd app.
- A restart of Home Assistant: commands to lights that are not the gateway work straight away, both with the hall light and with the stair cupboard relay as the Bluetooth entry point.
- Switching the Bluetooth entry point in the options.
- Simultaneous use with the Plejd app and a GWY-01.
- More than 30 hours without a single failed keep-alive, also at night.
- Sudden failure of the device that Home Assistant is connected through (power to the hall light switched off): Home Assistant was back through another device after about a minute, and lights that are not the gateway stayed controllable afterwards.
- Version 0.2.17: more than two hours connected after a restart, without a failed keep-alive, without an unprocessable message and without a repair notice.
- The guard against unprocessable messages: an empty message from the mesh, which makes pyplejd fail, was caught on the real installation. Only that one message was lost, and the connection kept working.
- The signal sensors and last seen.

**Not tested yet:**
- Relay outputs (the `switch` entity) on real hardware. They are covered by automated tests, and pyplejd 0.22.1 contains a fix for the relay state after a restart, but the maker has no device that Plejd reports as a relay. His REL-01-2P is set up as a light in the Plejd app, so it appears as a `light`.
- The repair notice for a long connection loss. We have only seen that it does not appear by mistake at startup.
- An ESPHome proxy, sudden disconnection of the Bluetooth adapter, the color temperature of lights that support it, and other installations.

## Support

This project is free (MIT). If you want to support the maker, you can do so via [Ko-fi](https://ko-fi.com/theginji).

## License and credits

MIT, see [LICENSE](LICENSE).

- [pyplejd](https://github.com/thomasloven/pyplejd) and [hass-plejd](https://github.com/thomasloven/hass-plejd) by Thomas Lovén (MIT). Without his work this would not exist.
- The community that worked out the Plejd protocol, as mentioned in the hass-plejd README.
- The icon is an original design. Only the color resembles Plejd's.
- Made with the help of Claude (Anthropic).
