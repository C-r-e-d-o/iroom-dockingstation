"""Media-Player: Lautstärke (absolut + up/down/mute) und Musiksteuerung.

volume: absolut via cmd:volume:<0..100>; sowie up/down/mute/unmute (Enum).
music:  play/pause/playpause/next/prev.
"""
from __future__ import annotations

from homeassistant.components.media_player import (
    MediaPlayerEntity, MediaPlayerEntityFeature, MediaPlayerState,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, VOLUME_RANGE
from .coordinator import ItopCoordinator
from .entity import ItopEntity


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry,
                            add: AddEntitiesCallback) -> None:
    coord: ItopCoordinator = hass.data[DOMAIN][entry.entry_id]
    add([ItopMediaPlayer(coord, entry.entry_id)])


class ItopMediaPlayer(ItopEntity, MediaPlayerEntity):
    _attr_supported_features = (
        MediaPlayerEntityFeature.VOLUME_SET
        | MediaPlayerEntityFeature.VOLUME_STEP
        | MediaPlayerEntityFeature.VOLUME_MUTE
        | MediaPlayerEntityFeature.PLAY
        | MediaPlayerEntityFeature.PAUSE
        | MediaPlayerEntityFeature.NEXT_TRACK
        | MediaPlayerEntityFeature.PREVIOUS_TRACK
    )

    def __init__(self, coord, entry_id):
        super().__init__(coord, entry_id, "audio")
        self._attr_name = "Audio"
        self._muted = False
        self._playing = False

    @property
    def state(self) -> MediaPlayerState:
        if not self.coordinator.available:
            return MediaPlayerState.OFF
        return MediaPlayerState.PLAYING if self._playing else MediaPlayerState.IDLE

    @property
    def volume_level(self) -> float | None:
        v = self.coordinator.inf("volume")
        if v is None or v == "":
            return None
        try:
            return max(0.0, min(1.0, int(float(v)) / 100.0))
        except (ValueError, TypeError):
            return None

    @property
    def is_volume_muted(self) -> bool:
        return self._muted

    async def async_set_volume_level(self, volume: float) -> None:
        lo, hi = VOLUME_RANGE
        pct = max(lo, min(hi, round(volume * 100)))
        await self.coordinator.client.send_raw(f"cmd:volume:{pct};")
        await self.coordinator.client.readback("volume")

    async def async_volume_up(self) -> None:
        await self.coordinator.client.cmd("volume", "up")
        await self.coordinator.client.readback("volume")

    async def async_volume_down(self) -> None:
        await self.coordinator.client.cmd("volume", "down")
        await self.coordinator.client.readback("volume")

    async def async_mute_volume(self, mute: bool) -> None:
        self._muted = mute
        await self.coordinator.client.cmd("volume", "mute" if mute else "unmute")
        self.async_write_ha_state()

    async def async_media_play(self) -> None:
        self._playing = True
        await self.coordinator.client.cmd("music", "play")
        self.async_write_ha_state()

    async def async_media_pause(self) -> None:
        self._playing = False
        await self.coordinator.client.cmd("music", "pause")
        self.async_write_ha_state()

    async def async_media_next_track(self) -> None:
        await self.coordinator.client.cmd("music", "next")

    async def async_media_previous_track(self) -> None:
        await self.coordinator.client.cmd("music", "prev")
