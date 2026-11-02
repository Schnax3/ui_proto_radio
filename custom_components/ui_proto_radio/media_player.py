"""Media-Player für UIProto/AirMusic-Internetradios (MediaYou) mit dynamischer JSON-Konfiguration."""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from datetime import timedelta
import aiohttp

from homeassistant.components.media_player import (
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
    MediaType,
)
from homeassistant.const import CONF_HOST
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(seconds=15)
MAX_VOLUME = 31

SOURCE_MAPPING = {
    "Internet Radio": 52,
    "Spotify Connect": 136,
    "Media-Center": 2,
    "UPnP": 8,
    "USB": 122,
    "DAB/DAB+": 91,
    "FM": 5,
    "Bluetooth": 104,
    "AUX": 47,
    "Lokale Station": 87,
    "my mediaU": 51,
}

SID_STATES = {
    "1": MediaPlayerState.IDLE,
    "2": MediaPlayerState.BUFFERING,
    "5": MediaPlayerState.BUFFERING,
    "6": MediaPlayerState.PLAYING,
    "7": MediaPlayerState.IDLE,
    "9": MediaPlayerState.PAUSED,
    "12": MediaPlayerState.BUFFERING,
    "14": MediaPlayerState.IDLE,
}

STATION_ID = re.compile(r"^\d+_\d+$")


def load_radio_config(model_identifier: str | None = None) -> dict:
    """Lädt die passende JSON-Konfiguration basierend auf dem erkannten Modell."""
    config_dir = os.path.join(os.path.dirname(__file__), "configs")
    
    # Bestimme Dateinamen anhand des Modells
    file_name = "default.json"
    if model_identifier and "sidney" in model_identifier.lower():
        file_name = "sidney.json"
    elif model_identifier and "dabman" in model_identifier.lower():
        file_name = "sidney.json"  # Nutzt gleiches Mapping

    file_path = os.path.join(config_dir, file_name)
    if not os.path.exists(file_path):
        file_path = os.path.join(config_dir, "default.json")

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            _LOGGER.info("UIProto Radio: Konfiguration geladen aus %s", file_name)
            return data
    except Exception as err:
        _LOGGER.error("Fehler beim Laden der Radio-Konfiguration: %s", err)
        return {"keys": {"power": 7, "mute": 8, "vol_up": 9, "vol_down": 10}}


def _tag(text: str, name: str) -> str | None:
    """Wert eines XML-ähnlichen Tags lesen."""
    match = re.search(rf"<{name}>(.*?)</{name}>", text, re.S | re.I)
    return match.group(1).strip() if match else None


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up UIProto Radio platform from a config entry (UI)."""
    host = entry.data[CONF_HOST]
    
    # Vorläufiger Client, um Modellinformationen (/init oder /irdevice.xml) abzufragen
    session = async_get_clientsession(hass)
    detected_model = "default"
    
    try:
        async with session.get(f"http://{host}/irdevice.xml", timeout=aiohttp.ClientTimeout(total=3)) as resp:
            if resp.status == 200:
                text = await resp.text()
                detected_model = _tag(text, "friendlyName") or "default"
    except Exception:
        try:
            async with session.get(f"http://{host}/init?language=de", timeout=aiohttp.ClientTimeout(total=3)) as resp:
                if resp.status == 200:
                    detected_model = "sidney"  # Fallback bei erfolgreichem /init
        except Exception:
            pass

    # Passende Konfiguration laden
    radio_config = load_radio_config(detected_model)

    player = UIProtoRadioPlayer(host, entry.entry_id, radio_config)
    async_add_entities([player], True)

    # Service registrieren
    if not hass.services.has_service(DOMAIN, "send_key"):
        async def async_send_key_service(call):
            entity_id = call.data.get("entity_id")
            key = call.data.get("key")
            for entity in hass.data.get(f"{DOMAIN}_entities", []):
                if not entity_id or entity.entity_id == entity_id:
                    await entity.async_send_key(key)

        hass.services.async_register(DOMAIN, "send_key", async_send_key_service)


class UIProtoRadioPlayer(MediaPlayerEntity):
    """Representation of a UIProto Internet Radio."""

    _attr_media_content_type = MediaType.MUSIC
    _attr_supported_features = (
        MediaPlayerEntityFeature.TURN_ON
        | MediaPlayerEntityFeature.TURN_OFF
        | MediaPlayerEntityFeature.VOLUME_SET
        | MediaPlayerEntityFeature.VOLUME_STEP
        | MediaPlayerEntityFeature.VOLUME_MUTE
        | MediaPlayerEntityFeature.SELECT_SOURCE
        | MediaPlayerEntityFeature.PLAY
        | MediaPlayerEntityFeature.PAUSE
        | MediaPlayerEntityFeature.STOP
        | MediaPlayerEntityFeature.NEXT_TRACK
        | MediaPlayerEntityFeature.PREVIOUS_TRACK
        | MediaPlayerEntityFeature.PLAY_MEDIA
    )

    def __init__(self, host, entry_id, config):
        """Initialize the radio with dynamic config."""
        self._host = host
        self._config = config
        self._keys = config.get("keys", {})
        self._attr_name = "Internetradio"
        self._attr_unique_id = f"{entry_id}_internet_radio"
        self._attr_state = MediaPlayerState.IDLE
        self._attr_volume_level = 0.5
        self._attr_is_volume_muted = False
        self._attr_source = None
        self._attr_source_list = list(SOURCE_MAPPING.keys())
        self._attr_media_title = None
        self._attr_media_artist = None
        self._attr_media_channel = None

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        self.hass.data.setdefault(f"{DOMAIN}_entities", []).append(self)

    async def async_will_remove_from_hass(self):
        await super().async_will_remove_from_hass()
        entities = self.hass.data.get(f"{DOMAIN}_entities", [])
        if self in entities:
            entities.remove(self)

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._host)},
            "name": f"UIProto ({self._config.get('model_name', 'Radio')})",
            "manufacturer": "MediaYou / OEM",
            "model": "UIProto Streaming Radio",
            "sw_version": "j61120190611h",
        }

    async def _get(self, path: str) -> str | None:
        url = f"http://{self._host}{path}"
        try:
            session = async_get_clientsession(self.hass)
            async with session.get(
                url, timeout=aiohttp.ClientTimeout(total=5), headers={"Connection": "close"}
            ) as response:
                return await response.text(errors="ignore")
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            _LOGGER.debug("Radio %s antwortet nicht (%s): %s", self._host, path, err)
            return None

    async def async_send_key_name(self, key_name: str):
        """Sendet eine Taste anhand ihres Namens aus der JSON-Config."""
        key_code = self._keys.get(key_name)
        if key_code is not None:
            await self.async_send_key(key_code)
        else:
            _LOGGER.warning("Taste '%s' ist in der Config nicht definiert", key_name)

    async def async_send_key(self, key):
        result = await self._get(f"/Sendkey?key={key}")
        if result is None:
            _LOGGER.warning("Taste %s konnte nicht gesendet werden", key)
        return result

    async def async_send_gochild(self, child_id):
        result = await self._get(f"/gochild?id={child_id}")
        if result is None:
            _LOGGER.warning("gochild %s konnte nicht gesendet werden", child_id)
        return result

    async def _refresh(self, delay: float = 1.0) -> None:
        await asyncio.sleep(delay)
        await self.async_update()
        self.async_write_ha_state()

    def _clear_media(self) -> None:
        self._attr_media_title = None
        self._attr_media_artist = None
        self._attr_media_channel = None

    async def async_turn_on(self):
        if self._attr_state != MediaPlayerState.OFF:
            return
        await self.async_send_key_name("power")
        await self._refresh(3)

    async def async_turn_off(self):
        if self._attr_state == MediaPlayerState.OFF:
            return
        await self.async_send_key_name("power")
        await self._refresh(3)

    async def async_volume_up(self):
        await self.async_send_key_name("vol_up")
        await self._refresh()

    async def async_volume_down(self):
        await self.async_send_key_name("vol_down")
        await self._refresh()

    async def async_set_volume_level(self, volume):
        vol_int = max(0, min(MAX_VOLUME, round(volume * MAX_VOLUME)))
        await self._get(f"/setvol?vol={vol_int}&mute=0")
        self._attr_volume_level = volume
        self._attr_is_volume_muted = False
        self.async_write_ha_state()

    async def async_mute_volume(self, mute):
        vol_int = round((self._attr_volume_level or 0) * MAX_VOLUME)
        await self._get(f"/setvol?vol={vol_int}&mute={1 if mute else 0}")
        self._attr_is_volume_muted = mute
        self.async_write_ha_state()

    async def async_select_source(self, source):
        if source in SOURCE_MAPPING:
            source_id = SOURCE_MAPPING[source]
            await self.async_send_key_name("home")
            await asyncio.sleep(0.4)
            await self.async_send_gochild(source_id)
            self._attr_source = source
            await self._refresh(1)

    async def async_play_media(self, media_type, media_id, **kwargs):
        media_id = str(media_id).strip()
        if not STATION_ID.match(media_id):
            return
        await self.async_send_gochild(media_id.split("_")[0])
        await asyncio.sleep(1)
        await self._get(f"/play_stn?id={media_id}")
        await self._refresh(2)

    async def async_media_play(self):
        if self._attr_state == MediaPlayerState.PLAYING:
            return
        await self.async_send_key_name("play_pause")
        await self._refresh()

    async def async_media_pause(self):
        if self._attr_state != MediaPlayerState.PLAYING:
            return
        await self.async_send_key_name("play_pause")
        await self._refresh()

    async def async_media_stop(self):
        await self._get("/stop")
        await self._refresh()

    async def async_media_next_track(self):
        await self.async_send_key_name("next")
        await self._refresh()

    async def async_media_previous_track(self):
        await self.async_send_key_name("prev")
        await self._refresh()

    async def async_update(self):
        text = await self._get("/playinfo")
        if text is None:
            self._attr_state = MediaPlayerState.OFF
            self._clear_media()
            return

        vol = _tag(text, "vol")
        if vol is not None and vol.isdigit():
            self._attr_volume_level = min(int(vol) / MAX_VOLUME, 1.0)
        mute = _tag(text, "mute")
        if mute is not None:
            self._attr_is_volume_muted = mute == "1"

        sid = _tag(text, "sid")
        self._attr_state = SID_STATES.get(sid, MediaPlayerState.IDLE)

        if self._attr_state in (
            MediaPlayerState.PLAYING,
            MediaPlayerState.PAUSED,
            MediaPlayerState.BUFFERING,
        ):
            self._attr_media_title = _tag(text, "song")
            self._attr_media_artist = _tag(text, "artist")
            self._attr_media_channel = _tag(text, "station_info")
        else:
            self._clear_media()
