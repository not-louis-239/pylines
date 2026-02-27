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

"""State management module for separating game state from other states"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Generator, Literal, cast

import pygame as pg
import OpenGL.GL as gl

import pylines.core.colours as cols
import pylines.core.constants as C
from pylines.core.asset_manager import FLine
from pylines.core.asset_manager_helpers import (
    ControlsSection,
    ControlsSectionID,
    MusicID,
)
from pylines.core.audio_manager import SFXChannelID
from pylines.core.custom_types import Colour, EventList
from pylines.core.paths import DIRS
from pylines.core.time_manager import (
    fetch_hour,
    sky_colour_from_hour,
)
from pylines.core.utils import clamp, draw_text, draw_transparent_rect, wrap_text
from pylines.game.managers.building_renderer import BuildingRenderer
from pylines.game.managers.cockpit_renderer import CockpitRenderer
from pylines.game.managers.controls_reference import ControlsReference
from pylines.game.managers.jukebox import Jukebox
from pylines.game.managers.map_menu import MapMenu
from pylines.game.managers.smoke_manager import SmokeManager
from pylines.game.managers.star_renderer import StarRenderer, StarRenderingData
from pylines.game.states import State, StateID
from pylines.objects.buttons import Button, ImageButton
from pylines.objects.objects import CrashReason, Plane
from pylines.objects.rotation_input_container import RotationInputContainer
from pylines.objects.scenery.ground import Ground
from pylines.objects.scenery.ocean import Ocean
from pylines.objects.scenery.sky import Moon, Sky, Sun

if TYPE_CHECKING:
    from pylines.core.custom_types import ScancodeWrapper, Surface
    from pylines.game.game import Game

@dataclass
class DialogMessage:
    active_time: int = 0  # milliseconds
    colour: Colour = cols.WHITE
    msg: str = ''

    def set_message(self, msg: str, colour: Colour = cols.WHITE, active_time: int = 2500):
        self.active_time = active_time
        self.msg = msg
        self.colour = colour

    def reset(self):
        self.set_message('', cols.WHITE, 0)

    def update(self, dt: int):
        self.active_time = max(self.active_time - dt, 0)

class GameScreen(State):
    def __init__(self, game: Game) -> None:
        """Purposefully lightweight constructor
        to avoid stalling during loading screen."""

        assets = game.assets
        super().__init__(game)
        assert self.game.env is not None

        self.warn_stall: bool = False
        self.warn_overspeed: bool = False
        self.time_elapsed: int = 0  # milliseconds

        self.dialog_box = DialogMessage()

        self.sky = Sky()
        self.sun = Sun(assets.images.sun)
        self.moon = Moon(assets.images.moon)
        self.plane = Plane(self.game.audio_manager, assets.sounds, self.dialog_box, self.game.env, RotationInputContainer())

        self.auto_screenshots_enabled: bool = False
        self.auto_screenshot_interval_ms: int = 30_000
        self._auto_screenshot_elapsed_ms: int = 0
        self._auto_screenshot_pending: bool = False

        # GPS destination
        self.gps_runway_index: int = 1  # start at second GPS destination

        # Pausing
        self.paused: bool = False

        # Font for text rendering
        self.font = pg.font.Font(assets.fonts.monospaced, 36)

        # Confirmation menus
        self.in_menu_confirmation: bool = False
        self.in_restart_confirmation: bool = False
        self.in_controls_screen: bool = False

        self.in_help_screen: bool = False
        self.help_screen_offset: float = 0
        self.help_max_offset: float = 0
        self.help_scroll_vel: float = 0

        self.continue_button = Button(
            (C.WN_W//2-400, C.WN_H//2), 250, 50, (0, 96, 96), (128, 255, 255),
            "Continue", self.fonts.monospaced, 30
        )
        self.restart_button = Button(
            (C.WN_W//2, C.WN_H//2), 250, 50, (0, 96, 96), (128, 255, 255),
            "Restart", self.fonts.monospaced, 30
        )
        self.menu_button = Button(
            (C.WN_W//2+400, C.WN_H//2), 250, 50, (0, 96, 96), (128, 255, 255),
            "Return to Menu", self.fonts.monospaced, 30
        )

        self.yes_button = Button(
            (C.WN_W//2-200, C.WN_H//2+20), 150, 50, (0, 96, 96), (128, 255, 255),
            "Yes", self.fonts.monospaced, 30
        )
        self.no_button = Button(
            (C.WN_W//2+200, C.WN_H//2+20), 150, 50, (0, 96, 96), (128, 255, 255),
            "No", self.fonts.monospaced, 30
        )

        self.controls_button = Button(
            (C.WN_W//2, C.WN_H - 100), 250, 50, (0, 96, 96), (128, 255, 255),
            "Controls", self.fonts.monospaced, 30
        )
        self.back_button = Button(
            (C.WN_W//2, C.WN_H - 70), 250, 50, (0, 96, 96), (128, 255, 255),
            "Back", self.fonts.monospaced, 30
        )
        self.crash_screen_restart_button = Button(
            (C.WN_W//2, C.WN_H//2 + 30), 180, 50, (0, 96, 96), (128, 255, 255),
            "Restart", self.fonts.monospaced, 30
        )

        self.help_button = ImageButton((C.WN_W - 75, C.WN_H - 75), self.images.help_icon)

        # Graphics
        self.hud_tex = gl.glGenTextures(1)
        gl.glBindTexture(gl.GL_TEXTURE_2D, self.hud_tex)

        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_S, gl.GL_CLAMP_TO_EDGE)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_T, gl.GL_CLAMP_TO_EDGE)

        # Allocate empty texture
        gl.glTexImage2D(gl.GL_TEXTURE_2D, 0, gl.GL_RGBA, C.WN_W, C.WN_H, 0, gl.GL_RGBA, gl.GL_UNSIGNED_BYTE, None)

        gl.glBindTexture(gl.GL_TEXTURE_2D, 0)
        self.hud_surface = pg.Surface((C.WN_W, C.WN_H), pg.SRCALPHA)

        # Cache rotated compasses to save resources when drawing
        self.cockpit_renderer = CockpitRenderer(self.game, self.plane)
        self.star_renderer = StarRenderer(StarRenderingData(), self.game.env, self.plane)
        self.controls_quick_ref = ControlsReference(self.game)
        self.show_cockpit: bool = True  # Start with cockpit visible

        self.smoke_manager = SmokeManager(assets.images)
        self.jukebox = Jukebox(self.game, self.game.assets.sounds.jukebox_tracks)

    def reset(self) -> None:
        self.in_menu_confirmation = False
        self.in_restart_confirmation = False
        self.paused = False

        self.plane.reset()
        self.gps_runway_index = 1

        self.game.audio_manager.channels[SFXChannelID.WIND].stop()
        self.game.audio_manager.channels[SFXChannelID.ENGINE_ACTIVE].stop()
        self.game.audio_manager.channels[SFXChannelID.ENGINE_AMBIENT].stop()

        self.game.audio_manager.channels[SFXChannelID.WARN_STALL].stop()
        self.game.audio_manager.channels[SFXChannelID.WARN_OVERSPEED].stop()

        self.game.audio_manager.channels[SFXChannelID.TERRAIN_SCRAPE].stop()

        self.sounds.jukebox_tracks[MusicID.OPEN_TWILIGHT].sound_obj.fadeout(1_500)
        self.dialog_box.reset()
        self.time_elapsed = 0

    def _build(self) -> Generator[tuple[float, str], None, None]:
        # TODO: Create a more centralised loading pipeline

        yield from self._init_ground(0.3, 0.45)

        self._init_ocean()
        yield 0.7, "Adding H₂O"

        self.building_renderer = BuildingRenderer(self.game)
        yield 0.85, "Making cities"

        self.map_menu = MapMenu(self.game, self.plane)
        yield 0.95, "Booting up GPS"

    def _init_ground(self, start: float, end: float):
        assert self.game.env is not None

        assets = self.game.assets
        ground_textures = {
            "sand_texture": assets.images.sand,
            "low_grass_texture": assets.images.low_grass,
            "high_grass_texture": assets.images.high_grass,
            "treeline_rock_texture": assets.images.treeline_rock,
            "alpine_rock_texture": assets.images.alpine_rock,
            "snow_texture": assets.images.snow,
            "noise": assets.world.noise,
        }

        self.ground = Ground(ground_textures, self.game.env)

        span = end - start
        for p, msg in self.ground._build():
            yield start + p * span, msg

    def _init_ocean(self):
        assert self.game.env is not None

        self.ocean = Ocean(self.game.assets.images.ocean, self.game.env)

    def take_screenshot(self, *, notify: bool = True) -> None:
        DIRS.data.screenshots.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"screenshot_{timestamp}.png"
        filepath = DIRS.data.screenshots / filename

        width, height = C.WN_W, C.WN_H
        gl.glPixelStorei(gl.GL_PACK_ALIGNMENT, 1)

        # Read RGB only to avoid alpha artifacts from the framebuffer
        pixel_data = gl.glReadPixels(0, 0, width, height, gl.GL_RGB, gl.GL_UNSIGNED_BYTE)

        assert isinstance(pixel_data, bytes)  # avoids static type checker errors
        surface = pg.image.frombuffer(pixel_data, (width, height), "RGB")
        surface = pg.transform.flip(surface, False, True)
        pg.image.save(surface, str(filepath))

        if notify:
            self.dialog_box.set_message(f"Screenshot saved: {filename}", (255, 240, 209))  # light yellow colour

    def draw_pause_screen(self) -> None:
        for button in (
            self.continue_button, self.restart_button,
            self.menu_button, self.help_button, self.controls_button
        ):
            button.draw(self.hud_surface)

        draw_text(
            self.hud_surface, (C.WN_W//2, C.WN_H*0.35), 'centre', 'centre',
            'Game Paused', (255, 255, 255), 50, self.fonts.monospaced
        )

    def draw_confirmation_menu(self) -> None:
        if self.in_menu_confirmation or self.in_restart_confirmation:
            draw_transparent_rect(
                self.hud_surface, (C.WN_W//2 - 400, C.WN_H//2 - 175), (800, C.WN_H*0.3),
                border_thickness=3
            )

            draw_text(
                self.hud_surface, (C.WN_W//2, C.WN_H*0.4), 'centre', 'centre',
                'Are you sure?', (255, 255, 255), 50, self.fonts.monospaced
            )

            for button in (self.yes_button, self.no_button):
                button.draw(self.hud_surface)

    def draw_controls_screen(self) -> None:
        self.back_button.draw(self.hud_surface)

        controls_sections: dict[ControlsSectionID, ControlsSection] = self.game.assets.texts.controls_sections  # Local alias

        draw_transparent_rect(
            self.hud_surface, (C.WN_W * 0.1, C.WN_H * 0.1), (C.WN_W * 0.8, C.WN_H*0.70),
            border_thickness=3
        )

        draw_text(
            self.hud_surface, (C.WN_W//2, C.WN_H*0.16), 'centre', 'centre',
            'Controls', (255, 255, 255), 50, self.fonts.monospaced
        )

        draw_text(self.hud_surface, (C.WN_W//2 - 480, C.WN_H*0.3), 'left', 'centre', ControlsSectionID.MAIN, (0, 192, 255), 40, self.fonts.monospaced)
        for i, (key, action) in enumerate(controls_sections[ControlsSectionID.MAIN].keys.items()):
            draw_text(self.hud_surface, (C.WN_W//2 - 480, C.WN_H * (0.38 + 0.04*i)), 'left', 'centre', key, (150, 230, 255), 27, self.fonts.monospaced)
            draw_text(self.hud_surface, (C.WN_W//2 - 360, C.WN_H * (0.38 + 0.04*i)), 'left', 'centre', action, cols.WHITE, 27, self.fonts.monospaced)

        draw_text(self.hud_surface, (C.WN_W//2 + 20, C.WN_H*0.26), 'left', 'centre', ControlsSectionID.DISPLAYS, (0, 192, 255), 25, self.fonts.monospaced)
        for i, (key, action) in enumerate(controls_sections[ControlsSectionID.DISPLAYS].keys.items()):
            draw_text(self.hud_surface, (C.WN_W//2 + 20, C.WN_H * (0.31 + 0.03*i)), 'left', 'centre', key, (150, 230, 255), 21, self.fonts.monospaced)
            draw_text(self.hud_surface, (C.WN_W//2 + 140, C.WN_H * (0.31 + 0.03*i)), 'left', 'centre', action, cols.WHITE, 21, self.fonts.monospaced)

        draw_text(self.hud_surface, (C.WN_W//2 + 20, C.WN_H*0.4), 'left', 'centre', ControlsSectionID.MAP, (0, 192, 255), 25, self.fonts.monospaced)
        for i, (key, action) in enumerate(controls_sections[ControlsSectionID.MAP].keys.items()):
            draw_text(self.hud_surface, (C.WN_W//2 + 20, C.WN_H * (0.45 + 0.03*i)), 'left', 'centre', key, (150, 230, 255), 21, self.fonts.monospaced)
            draw_text(self.hud_surface, (C.WN_W//2 + 140, C.WN_H * (0.45 + 0.03*i)), 'left', 'centre', action, cols.WHITE, 21, self.fonts.monospaced)
        note = controls_sections[ControlsSectionID.MAP].note
        assert note is not None
        draw_text(self.hud_surface, (C.WN_W//2 + 20, C.WN_H * (0.45 + 0.03 * (len(controls_sections[ControlsSectionID.MAP].keys) + 0.5))), 'left', 'centre', note, (255, 255, 255), 21, self.fonts.monospaced)

        draw_text(self.hud_surface, (C.WN_W//2 + 20, C.WN_H*0.64), 'left', 'centre', ControlsSectionID.UTILITIES, (0, 192, 255), 25, self.fonts.monospaced)
        for i, (key, action) in enumerate(controls_sections[ControlsSectionID.UTILITIES].keys.items()):
            draw_text(self.hud_surface, (C.WN_W//2 + 20, C.WN_H * (0.69 + 0.03*i)), 'left', 'centre', key, (150, 230, 255), 21, self.fonts.monospaced)
            draw_text(self.hud_surface, (C.WN_W//2 + 140, C.WN_H * (0.69 + 0.03*i)), 'left', 'centre', action, cols.WHITE, 21, self.fonts.monospaced)

    def draw_help_screen(self) -> None:
        draw_transparent_rect(
            self.hud_surface, (30, 30), (C.WN_W - 60, C.WN_H - 60), border_thickness=3
        )

        rect = self.images.logo.get_rect(center=(C.WN_W//2, 100))
        self.hud_surface.blit(self.images.logo, rect)
        draw_text(
            self.hud_surface, (rect.centerx, rect.bottom + 8), 'centre', 'top',
            "Help", (0, 192, 255), 36, self.fonts.monospaced
        )

        self.back_button.draw(self.hud_surface)

        left = 80
        top = rect.bottom + 80
        bottom = C.WN_H - 120
        width = C.WN_W - 320
        logical_y = top
        indent_px = 24
        scrollbar_w = 12
        scrollbar_x = left + width + 20

        visual_styles: dict[FLine.Style, tuple[int, Colour, bool]] = {
            FLine.Style.HEADING_1: (36, (0, 192, 255), False),
            FLine.Style.HEADING_2: (28, (0, 192, 255), False),
            FLine.Style.BULLET: (24, cols.WHITE, True),
            FLine.Style.NORMAL: (24, cols.WHITE, False),
        }

        for fline in self.game.assets.texts.help_lines:
            size, colour, bullet = visual_styles[fline.style]

            x = left + indent_px * fline.indent
            max_w = width - indent_px * fline.indent

            font = pg.font.Font(self.fonts.monospaced, size)
            if bullet:
                bullet_prefix = "• "
                prefix_w = font.size(bullet_prefix)[0]
                wrapped = wrap_text(fline.text, max_w - prefix_w, font)
                for i, line in enumerate(wrapped):
                    render_y = logical_y - self.help_screen_offset
                    if render_y + font.get_linesize() >= top and render_y <= bottom:
                        if i == 0:
                            draw_text(self.hud_surface, (x, render_y), 'left', 'top', bullet_prefix, colour, size, font)
                        draw_text(self.hud_surface, (x + prefix_w, render_y), 'left', 'top', line, colour, size, font)
                    logical_y += font.get_linesize() + 4
            else:
                for line in wrap_text(fline.text, max_w, font):
                    render_y = logical_y - self.help_screen_offset
                    if render_y + font.get_linesize() >= top and render_y <= bottom:
                        draw_text(self.hud_surface, (x, render_y), 'left', 'top', line, colour, size, font)
                    logical_y += font.get_linesize() + 4

            logical_y += 6  # extra spacing between FLine entries

        content_height = max(0, logical_y - top)
        view_height = max(0, bottom - top)
        self.help_max_offset = max(0, content_height - view_height)
        self.help_screen_offset = max(0, min(self.help_screen_offset, self.help_max_offset))

        scrollbar_h = max(0, bottom - top)
        bar_bg = pg.Rect(scrollbar_x, top, scrollbar_w, scrollbar_h)
        pg.draw.rect(self.hud_surface, (55, 55, 55), bar_bg)

        if content_height > 0:
            if self.help_max_offset == 0:
                thumb_h = scrollbar_h
                thumb_y = top
            else:
                thumb_h = max(24, int(scrollbar_h * (view_height / content_height)))
                max_thumb_y = top + scrollbar_h - thumb_h
                thumb_y = top + int((self.help_screen_offset / self.help_max_offset) * (max_thumb_y - top))

            thumb = pg.Rect(scrollbar_x, thumb_y, scrollbar_w, thumb_h)
            pg.draw.rect(self.hud_surface, (185, 185, 185), thumb)

    def draw_hud(self):

        self.hud_surface.fill((0, 0, 0, 0))  # clear with transparency

        # Show cockpit if cockpit is enabled
        # Always show cockpit if the plane has crashed
        if self.show_cockpit or self.plane.crashed:
            self.cockpit_renderer.draw(self.hud_surface, self.warn_stall, self.warn_overspeed)

        # Render map
        if self.map_menu.state.animation_open:
            self.map_menu.draw(self.hud_surface, self.map_show_advanced_info)

        # Render jukebox
        if self.jukebox.state.animation_open:
            self.jukebox.draw(self.hud_surface)

        # Render controls quick reference if it's visible
        if self.controls_quick_ref.state.animation_open:
            self.controls_quick_ref.draw(self.hud_surface)

        self.cockpit_renderer.draw_crash_flash(self.hud_surface)

        # Exit controls
        if self.time_elapsed < 5_000 or not self.plane.flyable:
            draw_text(self.hud_surface, (15, 30), 'left', 'centre', "Press Esc to pause", cols.WHITE, 30, self.fonts.monospaced)

        # Show dialog box
        if self.dialog_box.active_time > 0:
            text_size = 30

            text_length = len(self.dialog_box.msg)
            text_length_pix = text_length * text_size/2

            buffer = text_size * 0.7

            draw_transparent_rect(
                self.hud_surface, (C.WN_W//2 - text_length_pix/2 - buffer, C.WN_H*0.2 - text_size*1.2), (text_length_pix + 2*buffer, text_size*2.4), (0, 0, 0, 180), 2
            )
            draw_text(
                self.hud_surface, (C.WN_W//2, C.WN_H*0.2), 'centre', 'centre',
                self.dialog_box.msg, self.dialog_box.colour, text_size, self.fonts.monospaced
            )

        def show_crash_reason(reason: CrashReason) -> None:
            if reason == CrashReason.TERRAIN:
                ui_text = "COLLISION WITH TERRAIN"
            elif reason == CrashReason.OCEAN:
                ui_text = "COLLISION WITH OCEAN"
            elif reason == CrashReason.OBSTACLE:
                ui_text = "COLLISION WITH OBSTACLE"
            elif reason == CrashReason.RUNWAY:
                ui_text = "IMPROPER LANDING ON RUNWAY"

            draw_transparent_rect(
                self.hud_surface, (C.WN_W*0.28, C.WN_H*0.3), (C.WN_W*0.44, C.WN_H*0.3),
                (0, 0, 0, 180), 2
            )
            draw_text(self.hud_surface, (C.WN_W//2, C.WN_H*0.37), 'centre', 'centre', 'CRASH', (255, 0, 0), 50, self.fonts.monospaced)
            draw_text(self.hud_surface, (C.WN_W//2, C.WN_H*0.45), 'centre', 'centre', ui_text, cols.WHITE, 30, self.fonts.monospaced)

        # Show crash reason on screen
        if self.plane.crash_reason is not None:
            show_crash_reason(self.plane.crash_reason)
            self.crash_screen_restart_button.draw(self.hud_surface)

        # If paused, show overlay
        if self.paused:
            # Always show transparent dark overlay
            transparent_surface = pg.Surface((C.WN_W, C.WN_H), pg.SRCALPHA)
            transparent_surface.fill((0, 0, 0, 100))
            self.hud_surface.blit(transparent_surface, (0, 0))

            if self.in_controls_screen:
                self.draw_controls_screen()
            elif self.in_help_screen:
                self.draw_help_screen()
            else:
                self.draw_pause_screen()

        self.draw_confirmation_menu()  # always show confirmation menu if one is active

        # Upload HUD surface to OpenGL
        hud_data = pg.image.tostring(self.hud_surface, "RGBA", True)

        gl.glEnable(gl.GL_BLEND)
        gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)
        gl.glBindTexture(gl.GL_TEXTURE_2D, self.hud_tex)
        gl.glTexSubImage2D(gl.GL_TEXTURE_2D, 0, 0, 0, C.WN_W, C.WN_H, gl.GL_RGBA, gl.GL_UNSIGNED_BYTE, hud_data)
        gl.glBindTexture(gl.GL_TEXTURE_2D, 0)

        gl.glDisable(gl.GL_DEPTH_TEST)

        # Render HUD on top of 3D world
        gl.glEnable(gl.GL_TEXTURE_2D)

        gl.glBindTexture(gl.GL_TEXTURE_2D, self.hud_tex)
        gl.glColor4f(1, 1, 1, 1)

        gl.glMatrixMode(gl.GL_PROJECTION)
        gl.glPushMatrix()
        gl.glLoadIdentity()
        gl.glOrtho(0, C.WN_W, C.WN_H, 0, -1, 1)

        gl.glMatrixMode(gl.GL_MODELVIEW)
        gl.glPushMatrix()
        gl.glLoadIdentity()

        gl.glBegin(gl.GL_QUADS)

        gl.glTexCoord2f(0, 1); gl.glVertex2f(0, 0)
        gl.glTexCoord2f(1, 1); gl.glVertex2f(C.WN_W, 0)
        gl.glTexCoord2f(1, 0); gl.glVertex2f(C.WN_W, C.WN_H)
        gl.glTexCoord2f(0, 0); gl.glVertex2f(0, C.WN_H)
        gl.glEnd()

        gl.glPopMatrix()
        gl.glMatrixMode(gl.GL_PROJECTION)
        gl.glPopMatrix()
        gl.glMatrixMode(gl.GL_MODELVIEW)

        gl.glBindTexture(gl.GL_TEXTURE_2D, 0)
        gl.glEnable(gl.GL_DEPTH_TEST)
        gl.glDisable(gl.GL_TEXTURE_2D)

    def update(self, dt: int):

        assert self.game.env is not None
        assert self.game.env.prohibited_zones is not None

        self.time_elapsed += dt

        self.sun.update()
        self.moon.update()

        if self.paused:
            return

        self.dialog_box.update(dt)

        if self.plane.crashed:
            self.smoke_manager.update(dt)
            self.plane.increment_crash_timer(dt)

            self.dialog_box.reset()

            self.game.audio_manager.stop_all(exclude=[SFXChannelID.LANDING_SFX])

            return

        if self.auto_screenshots_enabled:
            self._auto_screenshot_elapsed_ms += dt
            if self._auto_screenshot_elapsed_ms >= self.auto_screenshot_interval_ms:
                self._auto_screenshot_pending = True
                self._auto_screenshot_elapsed_ms %= self.auto_screenshot_interval_ms

        # Jukebox menu update
        if not self.jukebox.state.visible:
            self.jukebox.state.animation_open -= (dt/1000) / C.JUKEBOX_MENU_TOGGLE_ANIMATION_DURATION
        else:
            self.jukebox.state.animation_open += (dt/1000) / C.JUKEBOX_MENU_TOGGLE_ANIMATION_DURATION
        self.jukebox.state.animation_open = clamp(self.jukebox.state.animation_open, (0, 1))

        # Map update
        if not self.map_menu.state.visible:
            self.map_menu.state.animation_open -= (dt/1000) / C.MAP_TOGGLE_ANIMATION_DURATION
        else:
            self.map_menu.state.animation_open += (dt/1000) / C.MAP_TOGGLE_ANIMATION_DURATION
        self.map_menu.state.animation_open = clamp(self.map_menu.state.animation_open, (0, 1))

        # Controls ref update
        if not self.controls_quick_ref.state.visible:
            self.controls_quick_ref.state.animation_open -= (dt/1000) / C.CONTROLS_REF_TOGGLE_ANIMATION_DURATION
        else:
            self.controls_quick_ref.state.animation_open += (dt/1000) / C.CONTROLS_REF_TOGGLE_ANIMATION_DURATION
        self.controls_quick_ref.state.animation_open = clamp(self.controls_quick_ref.state.animation_open, (0, 1))

        self.plane.update(dt)

        # Stall warning
        self.warn_stall = self.plane.stalled
        if self.warn_stall:
            if not self.game.audio_manager.channels[SFXChannelID.WARN_STALL].get_busy():
                self.game.audio_manager.channels[SFXChannelID.WARN_STALL].play(self.sounds.stall_warning, loops=-1)
        else:
            self.game.audio_manager.channels[SFXChannelID.WARN_STALL].stop()

        # Overspeed warning
        self.warn_overspeed = self.plane.vel.length() > self.plane.model.v_ne  # Both in m/s
        if self.warn_overspeed:
            if not self.game.audio_manager.channels[SFXChannelID.WARN_OVERSPEED].get_busy():
                self.game.audio_manager.channels[SFXChannelID.WARN_OVERSPEED].play(self.sounds.overspeed, loops=-1)
        else:
            self.game.audio_manager.channels[SFXChannelID.WARN_OVERSPEED].stop()

        # Update engine and wind sounds
        if not self.game.audio_manager.channels[SFXChannelID.WIND].get_busy():
            self.game.audio_manager.channels[SFXChannelID.WIND].play(self.sounds.wind, loops=-1)
        if not self.game.audio_manager.channels[SFXChannelID.ENGINE_AMBIENT].get_busy():
            self.game.audio_manager.channels[SFXChannelID.ENGINE_AMBIENT].play(self.sounds.engine_loop_ambient, loops=-1)
        if not self.game.audio_manager.channels[SFXChannelID.ENGINE_ACTIVE].get_busy():
            self.game.audio_manager.channels[SFXChannelID.ENGINE_ACTIVE].play(self.sounds.engine_loop_active, loops=-1)

        wind_sound_strength = (self.plane.vel.length() - 61.73) / 25.72  # start wind at 120 kn, full at 170
        self.game.audio_manager.channels[SFXChannelID.WIND].set_volume(clamp(wind_sound_strength, (0, 1)))

        throttle_sound_strength = self.plane.throttle_frac ** 1.8
        self.game.audio_manager.channels[SFXChannelID.ENGINE_ACTIVE].set_volume(throttle_sound_strength)

        # Terrain scrape sound
        if (not self.plane.over_runway) and self.plane.on_ground:
            if not self.game.audio_manager.channels[SFXChannelID.TERRAIN_SCRAPE].get_busy():
                self.game.audio_manager.channels[SFXChannelID.TERRAIN_SCRAPE].play(self.sounds.terrain_scrape, -1)
        else:
            self.game.audio_manager.channels[SFXChannelID.TERRAIN_SCRAPE].stop()

        # Prohibited zone warning sound
        self.show_prohibited_zone_warning = self.plane.over_prohibited_zone()
        if self.show_prohibited_zone_warning:
            if not self.game.audio_manager.channels[SFXChannelID.WARN_PROHIBITED].get_busy():
                self.game.audio_manager.channels[SFXChannelID.WARN_PROHIBITED].play(self.sounds.prohibited_zone_warning, loops=-1)
            self.dialog_box.set_message("Immediately exit this zone - penalties may apply", (255, 127, 0), 100)
        else:
            self.game.audio_manager.channels[SFXChannelID.WARN_PROHIBITED].stop()

        # Update BGM based on jukebox
        self.jukebox.update(dt)

    def take_input(self, keys: ScancodeWrapper, events: EventList, dt: int) -> None:
        # Screenshot - this needs to ALWAYS WORK
        if self.pressed(keys, pg.K_F5):
            self.take_screenshot()

        # Meta controls
        if self.pressed(keys, pg.K_ESCAPE):
            if self.in_controls_screen or self.in_help_screen:
                self.in_controls_screen = False
                self.in_help_screen = False
                self.help_screen_offset = 0
                self.help_scroll_vel = 0
            else:
                self.paused = not self.paused

                if self.paused:
                    self.jukebox.pause()
                else:
                    self.jukebox.unpause()

            # Stop all channels if pause button is pressed, except music
            # Then pause the music channel
            self.game.audio_manager.stop_all(exclude=[SFXChannelID.MUSIC])

        if self.paused and not (self.in_menu_confirmation or self.in_restart_confirmation):
            if self.controls_button.check_click(events) and not self.in_controls_screen and not self.in_help_screen:
                self.in_controls_screen = True
                self.in_help_screen = False
            elif self.help_button.check_click(events) and not self.in_controls_screen and not self.in_help_screen:
                self.in_help_screen = True
                self.in_controls_screen = False
            elif self.back_button.check_click(events) and (self.in_controls_screen or self.in_help_screen):
                self.in_controls_screen = False
                self.in_help_screen = False
                self.help_screen_offset = 0.0
                self.help_scroll_vel = 0.0

            if self.in_help_screen:
                scroll_accel = 0.004 * dt
                wheel_impulse = 25

                for event in events:
                    if event.type == pg.MOUSEWHEEL:
                        self.help_scroll_vel -= event.y * wheel_impulse

                if keys[pg.K_UP]:
                    self.help_scroll_vel -= scroll_accel
                if keys[pg.K_DOWN]:
                    self.help_scroll_vel += scroll_accel
                if self.pressed(keys, pg.K_PAGEUP):
                    self.help_scroll_vel -= 220
                if self.pressed(keys, pg.K_PAGEDOWN):
                    self.help_scroll_vel += 220

                self.help_screen_offset += self.help_scroll_vel

                self.help_scroll_vel *= 0.85
                if abs(self.help_scroll_vel) < 0.02:
                    self.help_scroll_vel = 0.0

                if self.help_screen_offset < 0:
                    self.help_screen_offset = 0
                    self.help_scroll_vel = 0.0
                elif self.help_screen_offset > self.help_max_offset:
                    self.help_screen_offset = self.help_max_offset
                    self.help_scroll_vel = 0.0

            if self.continue_button.check_click(events):
                self.paused = False

                self.jukebox.music_channel.unpause()
                self.jukebox.is_playing = True

            if self.restart_button.check_click(events):
                self.in_restart_confirmation = True

            if self.menu_button.check_click(events):
                self.in_menu_confirmation = True

            self.update_prev_keys(keys); return

        # Menu confirmation
        if self.in_menu_confirmation:
            if self.yes_button.check_click(events):
                self.game.enter_state(StateID.TITLE)

            if self.no_button.check_click(events):
                self.in_menu_confirmation = False

        # Restart confirmation
        if self.in_restart_confirmation:
            if self.yes_button.check_click(events):
                self.reset()

            if self.no_button.check_click(events):
                self.in_restart_confirmation = False

        # Toggle jukebox menu
        if self.pressed(keys, pg.K_j):
            self.jukebox.toggle_visibility()

        # Cockpit visibility toggling
        if self.pressed(keys, pg.K_F1):  # F1 to toggle HUD
            self.show_cockpit = not self.show_cockpit

        # Block flight controls if crashed or disabled
        if not self.plane.flyable:
            if self.crash_screen_restart_button.check_click(events):
                self.in_restart_confirmation = True

            self.update_prev_keys(keys)
            return

        # Jukebox controls
        if self.jukebox.state.visible:
            if self.pressed(keys, pg.K_MINUS):
                self.jukebox.volume -= self.jukebox.VOLUME_INCREMENT
            if self.pressed(keys, pg.K_EQUALS):
                self.jukebox.volume += self.jukebox.VOLUME_INCREMENT
            self.jukebox.volume = clamp(self.jukebox.volume, (0, 1))

            if self.pressed(keys, pg.K_LEFTBRACKET):
                self.jukebox.prev_track()
            if self.pressed(keys, pg.K_RIGHTBRACKET):
                self.jukebox.next_track()

            if self.pressed(keys, pg.K_SPACE):
                if self.jukebox.is_playing:
                    self.jukebox.pause()
                else:
                    self.jukebox.unpause()

        # Show/hide map
        if self.pressed(keys, pg.K_m):
            self.map_menu.toggle_visibility()

        # Show/hide quick ref for controls
        if self.pressed(keys, pg.K_o):
            self.controls_quick_ref.toggle_visibility()

        # Cycle GPS waypoint
        if self.pressed(keys, pg.K_g):
            self.plane.cycle_gps_waypoint()

        if self.map_menu.state.visible:
            # While map is shown: control zoom
            if keys[pg.K_w]:
                self.map_menu.viewport_zoom /= 2.5 ** (dt/1000)
            if keys[pg.K_s]:
                self.map_menu.viewport_zoom *= 2.5 ** (dt/1000)
            self.map_menu.viewport_zoom = clamp(self.map_menu.viewport_zoom, (C.MAP_ZOOM_MIN, C.MAP_ZOOM_MAX))
        else:
            # Throttle controls
            if keys[pg.K_w]:
                self.plane.throttle_frac += C.THROTTLE_SPEED * dt/1000
            if keys[pg.K_s]:
                self.plane.throttle_frac -= C.THROTTLE_SPEED * dt/1000
            self.plane.throttle_frac = clamp(self.plane.throttle_frac, (0, 1))

        # Show advanced info iff map is visible and advanced info key is held down
        self.map_show_advanced_info = self.map_menu.state.visible and keys[pg.K_h]

        # Turning or map panning
        if self.map_menu.state.visible:
            self.plane.rot_input_container.reset()  # zero out plane rotation inputs while map is shown
            panning_speed = self.map_menu.viewport_zoom * 150

            # Map shown -> pan map
            if keys[pg.K_UP]:
                self.map_menu.viewport_pos.z -= panning_speed * dt/1000
                self.map_menu.viewport_auto_panning = False
            if keys[pg.K_DOWN]:
                self.map_menu.viewport_pos.z += panning_speed * dt/1000
                self.map_menu.viewport_auto_panning = False
            if keys[pg.K_LEFT]:
                self.map_menu.viewport_pos.x -= panning_speed * dt/1000
                self.map_menu.viewport_auto_panning = False
            if keys[pg.K_RIGHT]:
                self.map_menu.viewport_pos.x += panning_speed * dt/1000
                self.map_menu.viewport_auto_panning = False

            # Reset map viewport pos
            if self.pressed(keys, pg.K_SPACE):
                self.map_menu.viewport_pos = self.plane.pos.copy()
                self.map_menu.viewport_auto_panning = True
        else:
            # Reset map viewport pos once map goes fully down
            if not self.map_menu.state.animation_open:
                self.map_menu.viewport_pos = self.plane.pos.copy()
                self.map_menu.viewport_auto_panning = True

            # Pitch
            direction: Literal[-1, 1] = -1 if self.game.save_data.invert_y_axis else 1

            pitch_input = 0  # temporary container
            if keys[pg.K_UP]:
                pitch_input += direction
            if keys[pg.K_DOWN]:
                pitch_input -= direction
            assert pitch_input in (-1, 0, 1)
            self.plane.rot_input_container.pitch_input = pitch_input

            # Turning
            roll_input = 0  # temporary container
            if keys[pg.K_LEFT]:
                roll_input -= 1
            if keys[pg.K_RIGHT]:
                roll_input += 1
            assert roll_input in (-1, 0, 1)
            self.plane.rot_input_container.roll_input = roll_input

        # Flaps
        if keys[pg.K_z]:  # Flaps up
            self.plane.flaps += C.FLAPS_SPEED * dt/1000
        if keys[pg.K_x]:  # Flaps down
            self.plane.flaps -= C.FLAPS_SPEED * dt/1000
        self.plane.flaps = clamp(self.plane.flaps, (0, 1))

        # Rudder
        if keys[pg.K_a]:
            self.plane.rudder -= C.RUDDER_SPEED * dt/1000 * min(1, self.plane.vel.length() / 10)
        if keys[pg.K_d]:
            self.plane.rudder += C.RUDDER_SPEED * dt/1000 * min(1, self.plane.vel.length() / 10)
        if not (keys[pg.K_a] or keys[pg.K_d]):
            one_minus_decay = (1 - C.RUDDER_SNAPBACK) ** (dt/1000)
            self.plane.rudder *= one_minus_decay
        self.plane.rudder = clamp(self.plane.rudder, (-1, 1))

        # Brakes
        self.plane.braking = keys[pg.K_b]  # b to brake

        self.update_prev_keys(keys)

    def draw(self, wn: Surface):
        assert self.game.env is not None
        assert self.game.config_presets is not None

        colour_scheme = sky_colour_from_hour(fetch_hour())

        gl.glClear(cast(int, gl.GL_COLOR_BUFFER_BIT) | cast(int, gl.GL_DEPTH_BUFFER_BIT))

        # Draw sky gradient background
        self.sky.draw(colour_scheme)

        gl.glMatrixMode(gl.GL_MODELVIEW)
        gl.glLoadIdentity()

        # Apply camera transformations based on plane's state
        # The order of operations is Yaw, then Pitch, then Roll.
        # OpenGL applies matrix transformations in reverse order of the calls.
        pitch, yaw, roll = self.plane.get_rot()
        gl.glRotatef(roll, 0, 0, 1) # 3. Roll
        gl.glRotatef(pitch, 1, 0, 0) # 2. Pitch
        gl.glRotatef(yaw, 0, 1, 0) # 1. Yaw

        camera_y = self.plane.pos.y + C.CAMERA_RADIUS
        gl.glTranslatef(-self.plane.pos.x, -camera_y, -self.plane.pos.z)

        camera_fwd = self.plane.native_fwd  # now uses native fwd vector, so no need to recalculate

        self.star_renderer.draw_stars()

        self.sun.draw()
        self.moon.draw()

        # Reduce brightness of drawn objects based on how many cloud layers there
        # are, and how much coverage each one has
        cloud_attenuation = 1.0
        for layer in self.game.config_presets.cloud_configs[self.game.save_data.cloud_config_idx].layers:
            cloud_attenuation *= (1 - layer.coverage * 0.2)

        self.ground.draw(cloud_attenuation)
        self.ocean.draw(cloud_attenuation)

        for runway in self.game.env.runways:
            runway.draw(cloud_attenuation)

        cloud_layers = self.game.config_presets.cloud_configs[self.game.save_data.cloud_config_idx]
        for cloud_layer in cloud_layers.layers:
            cloud_layer.draw(self.plane.pos, camera_fwd)

        self.building_renderer.draw(cloud_attenuation)

        if self.auto_screenshots_enabled and self._auto_screenshot_pending:
            self._auto_screenshot_pending = False
            self.take_screenshot(notify=True)

        self.draw_hud()
