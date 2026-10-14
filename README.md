# UIProto Internet Radio für Home Assistant

Eine moderne, lokal arbeitende Home Assistant Custom Integration für Internetradios mit MediaYou / UIProto-Firmware (getestet mit Firmware `j61120190611h`).

## Features

* **Vollständiger Media Player:** Steuerung von Power, Lautstärke, Mute, Wiedergabe und Pause direkt über eine native Home Assistant Entität (`media_player.internetradio`).
* **Config Flow (UI-Einrichtung):** Keine manuellen Einträge in der `configuration.yaml` nötig – füge das Radio bequem über die Benutzeroberfläche hinzu.
* **Quellen-Umschaltung:** Nahtloser Wechsel zwischen allen wichtigen Quellen (Internet Radio, Spotify Connect, Media-Center, UPnP, USB, Bluetooth, AUX u.v.m.).
* **Geräte- & Entitätsverwaltung:** Saubere Einbindung als vollwertiges Gerät inklusive eindeutiger `unique_id` und Geräteinformationen.
* **Modernes Branding:** Inklusive eigenem Logo für eine nahtlose Optik in Home Assistant.

---

## Installation

### Option 1: Über HACS (Empfohlen)
1. Öffne HACS in deinem Home Assistant.
2. Klicke oben rechts auf die drei Punkte und wähle **Benutzerdefinierte Repositories** (Custom Repositories).
3. Füge die URL deines GitHub-Repositories (`schnax3/ui_proto_radio`) hinzu und wähle als Kategorie **Integration**.
4. Suche nach **UIProto Internet Radio** in HACS, klicke auf Herunterladen und starte Home Assistant neu.

### Option 2: Manuelle Installation
1. Lade den Ordner `ui_proto_radio` aus diesem Repository herunter.
2. Kopiere den gesamten Ordner auf deinem Home Assistant Server in das Verzeichnis `/config/custom_components/`.
3. Starte Home Assistant neu.

---

## Einrichtung

1. Gehe in Home Assistant auf **Einstellungen** $\rightarrow$ **Geräte & Dienste**.
2. Klicke unten rechts auf **Integration hinzufügen**.
3. Suche nach **UIProto Internet Radio** und klicke darauf.
4. Gib die IP-Adresse deines Radios (z. B. `192.168.178.33`) ein. Fertig!

---

## Dashboard-Empfehlung

Für die optimale Steuerung empfiehlt sich eine maßgeschneiderte `custom:button-card`-Fernbedienung im Dashboard, die alle Schnellzugriffe auf Quellen und Navigation direkt bereitstellt.