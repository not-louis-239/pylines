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

from typing import TYPE_CHECKING

import pygame as pg

import pylines.core.colours as cols
import pylines.core.constants as C
from pylines.core.audio_manager import SFXChannelID
from pylines.core.asset_manager_helpers import ControlsSectionID, JukeboxTrack, MusicID
from pylines.core.custom_types import Surface
from pylines.core.utils import draw_text, draw_transparent_rect, format_to_song_length
from pylines.game.managers.pop_up_menus import PopupMenu

if TYPE_CHECKING:
    from pylines.game.game import Game

class Jukebox(PopupMenu):
    """Dedicated class for managing music."""

    VOLUME_INCREMENT: float = 0.1  # amount by which to change volume when pressing volume buttons

    def __init__(self, game: Game, tracks: dict[MusicID, JukeboxTrack]) -> None:
        super().__init__(game)

        if not tracks:
            # Jukebox needs tracks to play
            raise ValueError("Jukebox needs at least one track")

        # Must be initialised before attempting to fetch track IDs or track objects
        self.tracks = tracks
        self._cached_track_ids = list(self.tracks.keys())
        self._cached_track_objs = list(self.tracks.values())

        self.is_playing = False
        self.current_idx = 0
        self.volume: float = 1

        self.surface: Surface = Surface((540, 600), flags=pg.SRCALPHA)
        self.music_channel = self.game.audio_manager.channels[SFXChannelID.MUSIC]

        self.track_pos_secs: float = 0.0
        self.track_length_secs = self.calculate_track_length(self.get_current_track())

    def reset(self):
        self.track_pos_secs = 0
        self.track_length_secs = self.calculate_track_length(self.get_current_track())
        self.current_idx = 0

        self.is_playing = False
        self.music_channel.stop()
        self.reset_state()

    def get_current_track_id(self) -> MusicID:
        """Return the ID and sound object of the current track."""

        return self._cached_track_ids[self.current_idx]

    def get_current_track(self) -> JukeboxTrack:
        """Return the current track container."""

        return self._cached_track_objs[self.current_idx]

    def calculate_track_length(self, track: JukeboxTrack) -> float:
        if pg.mixer.get_init() is None:
            return 0  # fallback

        sample_rate = pg.mixer.get_init()[0]
        if sample_rate is None:
            # Use the precomputed sound object, this avoids wasting resources
            return track.sound_obj.get_length()

        try:
            samples = pg.sndarray.array(track.sound_obj)
            return samples.shape[0] / sample_rate
        except Exception:
            return track.sound_obj.get_length()

    def prev_track(self) -> None:
        if not self.tracks:
            raise ValueError("This jukebox has no tracks")

        self.current_idx = (self.current_idx - 1) % len(self.tracks)
        self.track_pos_secs = 0
        self.track_length_secs = self.calculate_track_length(self.get_current_track())
        self.music_channel.stop()  # prepares for new track

    def next_track(self) -> None:
        if not self.tracks:
            raise ValueError("This jukebox has no tracks")

        self.current_idx = (self.current_idx + 1) % len(self.tracks)
        self.track_pos_secs = 0
        self.track_length_secs = self.calculate_track_length(self.get_current_track())
        self.music_channel.stop()  # prepares for new track

    def update(self, dt: int) -> None:
        dt_seconds = dt / 1000
        self.music_channel.set_volume(self.volume)

        if self.track_length_secs > 0:
            if self.is_playing:
                if not self.music_channel.get_busy():
                    self.music_channel.play(self.get_current_track().sound_obj)

                self.track_pos_secs += dt_seconds
                self.track_pos_secs %= self.track_length_secs

    def pause(self) -> None:
        self.music_channel.pause()
        self.is_playing = False

    def unpause(self) -> None:
        self.music_channel.unpause()
        self.is_playing = True

    def draw(self, surface: Surface) -> None:
        # Clear jukebox menu surface
        self.surface.fill((0, 0, 0, 0))
        draw_transparent_rect(self.surface, (0, 0), (540, 600), (0, 0, 0, 150), 2)

        # Title
        draw_text(
            self.surface, (270, 48), 'centre', 'centre',
            "Jukebox", cols.WHITE, 35, self.game.assets.fonts.monospaced
        )

        # Show jukebox controls
        for i, (key, desc) in enumerate(self.game.assets.texts.controls_sections[ControlsSectionID.JUKEBOX].keys.items()):
            draw_text(
                self.surface, (16, 105 + 25 * i), 'left', 'centre',
                key, cols.BLUE, 20, self.game.assets.fonts.monospaced
            )
            draw_text(
                self.surface, (96, 105 + 25 * i), 'left', 'centre',
                desc, cols.WHITE, 20, self.game.assets.fonts.monospaced
            )

        # Volume display
        volume_display_centre_y = 190

        draw_text(
            self.surface, (16, volume_display_centre_y), 'left', 'centre',
            "Volume:", cols.WHITE, 20, self.game.assets.fonts.monospaced
        )

        # Volume bar
        bar_rect = pg.Rect(96, volume_display_centre_y - 6, 380, 12)
        buffer_width = 3
        pg.draw.rect(self.surface, cols.WHITE, bar_rect, width=1)

        inner_bar_width = (380 - 2 * buffer_width) * round(self.volume, ndigits=1)  # Round to 1 d.p. to avoid floating point offsets in display
        inner_bar_rect = pg.Rect(96 + buffer_width, volume_display_centre_y - 6 + buffer_width, inner_bar_width, 12 - 2 * buffer_width)
        pg.draw.rect(self.surface, cols.WHITE, inner_bar_rect)

        # Display currently playing song
        draw_text(
            self.surface, (270, 250), 'centre', 'centre',
            "Currently Playing", cols.WHITE, 20, self.game.assets.fonts.monospaced
        )

        sound_id = self.get_current_track_id()
        draw_text(
            self.surface, (270, 285), 'centre', 'centre',
            str(sound_id), cols.WHITE, 30, self.game.assets.fonts.monospaced
        )

        # Song progress bar
        progress_bar_centre_y = 325
        progress_bar_left = 80
        progress_bar_w = 380
        progress_bar_h = 10
        progress_buffer = 2

        if self.track_length_secs > 0:
            progress = self.track_pos_secs / self.track_length_secs
        else:
            progress = 0.0  # default, prevents ZeroDivisionError

        outer_rect = pg.Rect(progress_bar_left, progress_bar_centre_y - progress_bar_h // 2, progress_bar_w, progress_bar_h)
        pg.draw.rect(self.surface, cols.WHITE, outer_rect, width=1)

        inner_w = int((progress_bar_w - 2 * progress_buffer) * progress)
        inner_rect = pg.Rect(
            progress_bar_left + progress_buffer,
            progress_bar_centre_y - progress_bar_h // 2 + progress_buffer,
            inner_w,
            progress_bar_h - 2 * progress_buffer
        )
        pg.draw.rect(self.surface, cols.WHITE, inner_rect)

        # Show durations
        display_pos = format_to_song_length(self.track_pos_secs)
        display_length = format_to_song_length(self.track_length_secs)

        draw_text(
            self.surface, (progress_bar_left - 15, progress_bar_centre_y), 'right', 'centre',
            display_pos, cols.WHITE, 20, self.game.assets.fonts.monospaced
        )
        draw_text(
            self.surface, (progress_bar_left + progress_bar_w + 15, progress_bar_centre_y), 'left', 'centre',
            display_length, cols.WHITE, 20, self.game.assets.fonts.monospaced
        )

        # Blit entire display onto target surface
        blit_y = C.WN_H - (C.WN_H * 0.93) * self.state.animation_open
        surface.blit(self.surface, (C.WN_W/2 - 270, blit_y))
