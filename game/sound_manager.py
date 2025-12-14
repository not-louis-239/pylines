from __future__ import annotations
from typing import TYPE_CHECKING
import pygame as pg

if TYPE_CHECKING:
    from core.asset_manager import Sounds

class SoundManager:
    """
    A class to manage the engine sounds, using two channels for smooth,
    interrupt-safe cross-fading by manually controlling volume.
    """

    def __init__(self, sounds: Sounds):
        """
        Initialise the SoundManager.

        Args:
            sounds: The sounds asset bank.
        """
        self.sounds = sounds
        self.engine_loops = [
            sounds.engine_idle_loop,
            sounds.engine_20p_loop,
            sounds.engine_40p_loop,
            sounds.engine_60p_loop,
            sounds.engine_80p_loop,
            sounds.engine_full_loop,
        ]

        self.FADE_TIME_MS = 400

        # ch1 is for the dominant/fading-out sound
        # ch2 is for the incoming/fading-in sound
        self.ch1 = pg.mixer.Channel(1)
        self.ch2 = pg.mixer.Channel(2)

        self.ch1.set_volume(1.0)
        self.ch2.set_volume(0.0)

        self.current_sound_ch1: pg.mixer.Sound | None = None
        self.current_sound_ch2: pg.mixer.Sound | None = None

        self.transition_end_time = 0

    def _get_sound_from_throttle(self, throttle_frac: float) -> pg.mixer.Sound:
        if throttle_frac < 0.01:
            idx = 0
        elif throttle_frac < 0.2:
            idx = 1
        elif throttle_frac < 0.4:
            idx = 2
        elif throttle_frac < 0.6:
            idx = 3
        elif throttle_frac < 0.8:
            idx = 4
        else:
            idx = 5
        return self.engine_loops[idx]

    def update(self, throttle_frac: float):
        """
        Update the engine sound based on the throttle, cross-fading between sounds.
        """
        now = pg.time.get_ticks()
        desired_sound = self._get_sound_from_throttle(throttle_frac)

        # --- Part 1: Handle ongoing transitions ---
        if now < self.transition_end_time:
            time_left = self.transition_end_time - now
            progress = time_left / self.FADE_TIME_MS

            # ch1 fades out, ch2 fades in
            self.ch1.set_volume(progress)
            self.ch2.set_volume(1.0 - progress)
        elif self.current_sound_ch2:
            # Transition is over. Promote ch2 to ch1.
            self.ch1.stop()
            self.ch1, self.ch2 = self.ch2, self.ch1
            self.current_sound_ch1, self.current_sound_ch2 = self.current_sound_ch2, None
            self.ch1.set_volume(1.0)
            self.ch2.set_volume(0.0)

        # --- Part 2: Check if a new transition is needed ---
        is_in_transition = now < self.transition_end_time

        # If the desired sound is not our main sound and not the one we are already fading to
        if desired_sound != self.current_sound_ch1 and desired_sound != self.current_sound_ch2:
            if self.current_sound_ch1 is None:
                # This is the very first sound to be played.
                self.ch1.play(desired_sound, loops=-1)
                self.current_sound_ch1 = desired_sound
                self.ch1.set_volume(1.0)
            else:
                # A new transition is needed. The new sound will play on ch2.
                self.ch2.play(desired_sound, loops=-1)
                self.current_sound_ch2 = desired_sound
                self.ch2.set_volume(0.0)
                self.transition_end_time = now + self.FADE_TIME_MS


    def stop(self):
        """Stop all engine sounds on both channels."""
        self.ch1.stop()
        self.ch2.stop()
        self.current_sound_ch1 = None
        self.current_sound_ch2 = None
        self.transition_end_time = 0
