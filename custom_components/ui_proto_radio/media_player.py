"""Media-Player für UIProto/AirMusic-Internetradios (MediaYou)."""
from __future__ import annotations

import asyncio
import logging
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

# --- Tastencodes (Sendkey). Pro Modell verschieden, hier zentral anpassbar ---
KEY_POWER = 7          # von dir gefunden (Toggle)
KEY_MUTE = 8
KEY_VOL_UP = 9
KEY_VOL_DOWN = 10
KEY_PLAY_PAUSE = 29    # Toggle laut KINGS-Tabelle (unverifiziert beim Sidney)
KEY_NEXT = 31          # unverifiziert
KEY_PREV = 32          # unverifiziert

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

# sid-Werte aus <playinfo> (Doku zu einem Lenco-Radio, beim Sidney unverifiziert)
SID_STATES = {
    "1": MediaPlayerState.IDLE,        # nicht spielend
    "2": MediaPlayerState.BUFFERING,   # buffering
    "5": MediaPlayerState.BUFFERING,   # Buffer 100 %
    "6": MediaPlayerState.PLAYING,     # spielt
    "7": MediaPlayerState.IDLE,        # Wiedergabe endet
    "9": MediaPlayerState.PAUSED,      # pausiert
    "12": MediaPlayerState.BUFFERING,  # liest Datei
    "14": MediaPlayerState.IDLE,       # Verbindung fehlgeschlagen
}

STATION_ID = re.compile(r"^\d+_\d+$")


def _tag(text: str, name: str) -> str | None:
    """Wert eines XML-ähnlichen Tags lesen (das Radio escaped Sonderzeichen nicht)."""
    match = re.search(rf"<{name}>(.*?)</{name}>", text, re.S | re.I)
    return match.group(1).strip() if match else None


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up UIProto Radio platform from a config entry (UI)."""
    host = entry.data[CONF_HOST]
    async_add_entities([UIProtoRadioPlayer(host, entry.entry_id)], True)


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

    def __init__(self, host, entry_id):
        """Initialize the radio."""
        self._host = host
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

    @property
    def device_info(self):
        """Return device information about this radio."""
        return {
            "identifiers": {(DOMAIN, self._host)},
            "name": "UIProto Internet Radio",
            "manufacturer": "MediaYou / OEM",
            "model": "UIProto Streaming Radio",
            "sw_version": "j61120190611h",
        }

    # ------------------------------------------------------------------
    # Hilfsfunktionen
    # ------------------------------------------------------------------
    async def _get(self, path: str) -> str | None:
        """GET-Anfrage ans Radio. Gibt None zurück, wenn es nicht antwortet."""
        url = f"http://{self._host}{path}"
        try:
            session = async_get_clientsession(self.hass)
            async with session.get(
                url, timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                return await response.text(errors="ignore")
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            _LOGGER.debug("Radio %s antwortet nicht (%s): %s", self._host, path, err)
            return None

    async def async_send_key(self, key):
        """Send key command to radio."""
        result = await self._get(f"/Sendkey?key={key}")
        if result is None:
            _LOGGER.warning("Taste %s konnte nicht gesendet werden", key)
        return result

    async def async_send_gochild(self, child_id):
        """Send gochild command to radio."""
        result = await self._get(f"/gochild?id={child_id}")
        if result is None:
            _LOGGER.warning("gochild %s konnte nicht gesendet werden", child_id)
        return result

    async def _refresh(self, delay: float = 1.0) -> None:
        """Kurz warten, dann Status neu lesen und in HA anzeigen."""
        await asyncio.sleep(delay)
        await self.async_update()
        self.async_write_ha_state()

    def _clear_media(self) -> None:
        self._attr_media_title = None
        self._attr_media_artist = None
        self._attr_media_channel = None

    # ------------------------------------------------------------------
    # Ein / Aus (Taste 7 ist ein Toggle, darum nur senden, wenn nötig)
    # ------------------------------------------------------------------
    async def async_turn_on(self):
        if self._attr_state != MediaPlayerState.OFF:
            return
        await self.async_send_key(KEY_POWER)
        await self._refresh(3)

    async def async_turn_off(self):
        if self._attr_state == MediaPlayerState.OFF:
            return
        await self.async_send_key(KEY_POWER)
        await self._refresh(3)

    # ------------------------------------------------------------------
    # Lautstärke
    # ------------------------------------------------------------------
    async def async_volume_up(self):
        await self.async_send_key(KEY_VOL_UP)
        await self._refresh()

    async def async_volume_down(self):
        await self.async_send_key(KEY_VOL_DOWN)
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

    # ------------------------------------------------------------------
    # Quelle und Sender
    # ------------------------------------------------------------------
    async def async_select_source(self, source):
        if source in SOURCE_MAPPING:
            await self.async_send_gochild(SOURCE_MAPPING[source])
            self._attr_source = source
            self.async_write_ha_state()

    async def async_play_media(self, media_type, media_id, **kwargs):
        """Sender per ID abspielen, z. B. media_id: "91_6" (Menü-ID_Nummer)."""
        media_id = str(media_id).strip()
        if not STATION_ID.match(media_id):
            _LOGGER.error(
                "Ungültige Sender-ID %s (erwartet z. B. 91_6)", media_id
            )
            return
        # Erst in das passende Menü wechseln, sonst kann das Radio hängen bleiben
        await self.async_send_gochild(media_id.split("_")[0])
        await asyncio.sleep(1)
        await self._get(f"/play_stn?id={media_id}")
        await self._refresh(2)

    # ------------------------------------------------------------------
    # Wiedergabe
    # ------------------------------------------------------------------
    async def async_media_play(self):
        if self._attr_state == MediaPlayerState.PLAYING:
            return
        await self.async_send_key(KEY_PLAY_PAUSE)
        await self._refresh()

    async def async_media_pause(self):
        if self._attr_state != MediaPlayerState.PLAYING:
            return
        await self.async_send_key(KEY_PLAY_PAUSE)
        await self._refresh()

    async def async_media_stop(self):
        await self._get("/stop")
        await self._refresh()

    async def async_media_next_track(self):
        await self.async_send_key(KEY_NEXT)
        await self._refresh()

    async def async_media_previous_track(self):
        await self.async_send_key(KEY_PREV)
        await self._refresh()

    # ------------------------------------------------------------------
    # Status lesen
    # ------------------------------------------------------------------
    async def async_update(self):
        text = await self._get("/playinfo")
        if text is None:
            # Keine Antwort: Standby oder nicht erreichbar (nicht unterscheidbar)
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