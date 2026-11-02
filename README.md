# UIProto Internet Radio for Home Assistant

A modern, locally operating Home Assistant custom integration for internet radios with MediaYou / UIProto firmware (tested with firmware `j61120190611h`).

## Features

* **Full Media Player:** Control power, volume, mute, playback, and pause directly through a native Home Assistant entity (`media_player.internetradio`).
* **Config Flow (UI Setup):** No manual entries in `configuration.yaml` required – simply add your radio through the Home Assistant user interface.
* **Source Switching:** Seamlessly switch between all major sources (Internet Radio, Spotify Connect, Media Center, UPnP, USB, Bluetooth, AUX, and more).
* **Device & Entity Management:** Clean integration as a fully registered device, including a unique `unique_id` and device information.
* **Modern Branding:** Includes a custom logo for a seamless look and feel in Home Assistant.

---

## Installation

### Option 1: Via HACS (Recommended)

1. Open HACS in Home Assistant.
2. Click the three dots in the top-right corner and select **Custom repositories**.
3. Add your GitHub repository URL (`schnax3/ui_proto_radio`) and select **Integration** as the category.
4. Search for **UIProto Internet Radio** in HACS, click **Download**, and restart Home Assistant.

### Option 2: Manual Installation

1. Download the `ui_proto_radio` folder from this repository.
2. Copy the entire folder to the `/config/custom_components/` directory on your Home Assistant server.
3. Restart Home Assistant.

---

## Setup

1. In Home Assistant, navigate to **Settings** → **Devices & Services**.
2. Click **Add Integration** in the bottom-right corner.
3. Search for **UIProto Internet Radio** and select it.
4. Enter your radio's IP address (e.g. `192.168.178.33`). That's it!

---

## Dashboard Recommendation

For the best user experience, we recommend using a custom `custom:button-card` remote control in your dashboard, providing quick access to all sources and navigation controls.

---

## Acknowledgements

Thanks to everyone who helped me build this project!

Special thanks to:
- @My Brother
