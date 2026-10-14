import logging
import aiohttp

from homeassistant.components.media_player import (
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
)
from homeassistant.const import CONF_HOST, STATE_PLAYING, STATE_IDLE, STATE_OFF
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

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

async def async_setup_entry(hass, entry, async_add_entities):
    """Set up UIProto Radio platform from a config entry (UI)."""
    host = entry.data[CONF_HOST]
    async_add_entities([UIProtoRadioPlayer(host)], True)

class UIProtoRadioPlayer(MediaPlayerEntity):
    """Representation of a UIProto Internet Radio."""

    def __init__(self, host):
        """Initialize the radio."""
        self._host = host
        self._attr_name = "Internetradio"
        self._state = STATE_IDLE
        self._volume = 0.5
        self._muted = False
        self._source = None
        self._media_title = None

    @property
    def state(self):
        return self._state

    @property
    def volume_level(self):
        return self._volume

    @property
    def is_volume_muted(self):
        return self._muted

    @property
    def source(self):
        return self._source

    @property
    def source_list(self):
        return list(SOURCE_MAPPING.keys())

    @property
    def media_title(self):
        return self._media_title

    @property
    def supported_features(self):
        """Return the supported features."""
        return (
            MediaPlayerEntityFeature.TURN_ON
            | MediaPlayerEntityFeature.TURN_OFF
            | MediaPlayerEntityFeature.VOLUME_SET
            | MediaPlayerEntityFeature.VOLUME_STEP
            | MediaPlayerEntityFeature.VOLUME_MUTE
            | MediaPlayerEntityFeature.SELECT_SOURCE
            | MediaPlayerEntityFeature.PLAY
            | MediaPlayerEntityFeature.PAUSE
        )

    async def async_send_key(self, key):
        """Send key command to radio."""
        url = f"http://{self._host}/Sendkey?key={key}"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=5) as response:
                    return await response.text()
        except Exception as e:
            _LOGGER.error("Error sending key %s: %s", key, e)

    async def async_send_gochild(self, child_id):
        """Send gochild command to radio."""
        url = f"http://{self._host}/gochild?id={child_id}"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=5) as response:
                    return await response.text()
        except Exception as e:
            _LOGGER.error("Error sending gochild ID %s: %s", child_id, e)

    async def async_turn_on(self):
        await self.async_send_key(7)

    async def async_turn_off(self):
        await self.async_send_key(7)

    async def async_volume_up(self):
        await self.async_send_key(9)

    async def async_volume_down(self):
        await self.async_send_key(10)

    async def async_set_volume_level(self, volume):
        vol_int = int(volume * 31)
        url = f"http://{self._host}/setvol?vol={vol_int}&mute=0"
        async with aiohttp.ClientSession() as session:
            await session.get(url)
        self._volume = volume

    async def async_mute_volume(self, mute):
        await self.async_send_key(8)
        self._muted = mute

    async def async_select_source(self, source):
        if source in SOURCE_MAPPING:
            child_id = SOURCE_MAPPING[source]
            await self.async_send_gochild(child_id)
            self._source = source

    async def async_media_play(self):
        await self.async_send_key(29)

    async def async_media_pause(self):
        await self.async_send_key(30)

    async def async_update(self):
        url = f"http://{self._host}/playinfo"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=3) as response:
                    text = await response.text()
                    if "<sid>6</sid>" in text:
                        self._state = STATE_PLAYING
                    else:
                        self._state = STATE_IDLE
        except Exception:
            self._state = STATE_OFF