# Copyright 2025-2026 Louis Masarei-Boulton
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from enum import IntEnum

import pygame as pg

from pylines.core.asset_manager_helpers import MusicID
from pylines.game.states import StateID

class SFXChannelID(IntEnum):
    # Music
    MUSIC = 0

    # Engine
    ENGINE_AMBIENT = 1
    ENGINE_ACTIVE = 2
    WIND = 3

    # Warnings
    WARN_STALL = 4
    WARN_OVERSPEED = 5
    WARN_PROHIBITED = 6

    # Other
    TERRAIN_SCRAPE = 7
    LANDING_SFX = 8

class AudioManager:
    def __init__(self, game) -> None:
        # Initialise dictionary of channel entries
        self.game = game
        self.channels: dict[SFXChannelID, pg.mixer.Channel] = {}

        try:
            for channel_id in SFXChannelID:
                self.channels[channel_id] = pg.mixer.Channel(channel_id)
        except IndexError:
            # Raise an error to indicate insufficient channels
            current_limit = pg.mixer.get_num_channels()
            num_required = len(SFXChannelID)
            raise RuntimeError(
                f"Insufficient channels for AudioManager (required = {num_required}, available = {current_limit})."
                f"Consider using pg.mixer.set_num_channels({num_required}) "
                f"in main.py to increase the channel limit."
            )

    def on_state_change(self, prev_state: StateID, current_state: StateID) -> None:
        menu_states = (StateID.TITLE, StateID.SETTINGS, StateID.BRIEFING, StateID.CREDITS)
        was_in_menu = prev_state in menu_states
        is_entering_menu = current_state in menu_states

        # Fade out music if leaving a menu state for a non-menu state
        if was_in_menu and not is_entering_menu:
            self.channels[SFXChannelID.MUSIC].fadeout(1500)

        # Play music if entering a menu state from a non-menu state or if transitioning between menu states and music is not playing                                                                                                                          │
        elif is_entering_menu and (not was_in_menu or not self.channels[SFXChannelID.MUSIC].get_busy()):
            self.channels[SFXChannelID.MUSIC].play(self.game.assets.sounds.jukebox_tracks[MusicID.OPEN_TWILIGHT], loops=-1)

    def stop_all(self, *, exclude: list[SFXChannelID] | None = None) -> None:
        """Stops all registered channels, except those in `exclude`.
        Stops all channels if no excluded channels are given."""

        exclude = exclude or []

        for channel_id, channel in self.channels.items():
            # Stop only channels not in `exclude`
            if channel_id not in exclude:
                channel.stop()
