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

"""General purpose module in which to place simulation objects."""
from __future__ import annotations
from typing import TYPE_CHECKING
from math import asin, cos, degrees
from math import radians as rad
from math import sin

from OpenGL import GL as gl
import pygame as pg

from pylines.core.asset_manager import Sounds
from pylines.core.constants import (AIR_DENSITY, EPSILON, GRAVITY, PLANE_MODELS, PRACTISE_LIMIT, PlaneModel)
from pylines.core.custom_types import Surface
from pylines.core.utils import clamp

if TYPE_CHECKING:
    from pylines.game.screens.game_screen import DialogMessage
    from pylines.objects.scenery import Ground

class Entity:
    """Mental basis for all in-game physical objects"""

    def __init__(self, x: float, y: float, z: float) -> None:
        self.pos: pg.Vector3 = pg.Vector3(x, y, z)

    def update(self, dt):
        pass

    def draw(self, wn: Surface):
        pass

class Plane(Entity):
    def __init__(self, sounds: Sounds, dialog_box: DialogMessage, ground: Ground):
        super().__init__(0, 0, 0)
        self.model: PlaneModel = PLANE_MODELS["Cessna 172"]
        self.sounds = sounds
        self.dialog_box = dialog_box
        self.ground = ground
        self.reset()

    @property
    def crashed(self) -> bool:
        return self.crash_reason is not None

    @property
    def disabled(self) -> bool:
        return self.damage_level == 1  # Fully damaged

    @property
    def flyable(self) -> bool:
        return not self.crashed and not (
            self.disabled and self.on_ground
        )

    @property
    def stalling(self) -> bool:
        return self.aoa > self.model.stall_angle

    def reset(self) -> None:
        self.pos = pg.Vector3(0, self.ground.get_height(0, 0), 0)
        self.vel = pg.Vector3(0, 0, 0)
        self.acc = pg.Vector3(0, 0, 0)

        self.throttle_frac: float = 0  # from 0 to 1
        self.flaps: float = 0  # 0 = down, 1 = up
        self.rudder: float = 0  # from -1 to 1 (deflection)
        self.braking = False

        self.rot = pg.Vector3(0, 0, 0)  # pitch, yaw, roll
        self.rot_rate = pg.Vector3(0, 0, 0)
        self.show_stall_warning: bool = False

        self.aoa = 0  # degrees
        self.on_ground = True
        self.crash_reason = None
        self.damage_level = 0

    def process_landing(self):
        def good_landing():
            self.sounds.good_landing.play()
            self.dialog_box.set_message("Good landing!", (0, 255, 0))

        def hard_landing():
            self.sounds.hard_landing.play()
            self.dialog_box.set_message("Whoops. Hard landing.", (255, 200, 0))

        # TODO: Collision with buildings and ocean should be auto-lethal
        # (add once buildings and ocean are implemented)

        def crash(*, damage_taken: float = 0.0, lethal: bool = False, reason: str = 'ground'):
            self.damage_level = 1 if lethal else min(self.damage_level + damage_taken, 1)

            if self.damage_level >= 1:
                self.sounds.crash.play()
                self.crash_reason = reason
                return

            self.sounds.hard_landing.play()
            self.dialog_box.set_message("Hard landing. Damage sustained.", (255, 80, 0))

        # Check landing for quality
        pitch, yaw, roll = self.rot
        roll = (roll+180)%360 - 180  # Normalise

        # Safety parameters
        SAFE_VS = -1.7  # m/s
        MAX_OK_VS = -4
        MAX_SAFE_PITCH = 12
        MAX_SAFE_ROLL = 8

        # Impact metrics
        vs = -self.vel.y
        roll_mag = abs(roll)
        pitch_mag = abs(pitch)

        # Normalised excess (0–1)
        vs_factor = max(0, ((vs - SAFE_VS) / (MAX_OK_VS - SAFE_VS))) ** 2
        roll_factor = min(roll_mag / MAX_SAFE_ROLL, 3)
        pitch_factor = min(pitch_mag / MAX_SAFE_PITCH, 2)

        # Weighted damage
        impact_severity = (
            0.6 * vs_factor +
            0.25 * roll_factor +
            0.15 * pitch_factor
        )

        visual_pitch = -pitch  # Pitch is inverted in OpenGL
        if visual_pitch > MAX_SAFE_PITCH:  # nose up too much
            impact_severity *= 1 + 0.02 * (visual_pitch - MAX_SAFE_PITCH)
        elif visual_pitch < -MAX_SAFE_PITCH:  # nose down too much
            impact_severity *= 1 + 0.04 * -(visual_pitch - -MAX_SAFE_PITCH)

        MAX_SAFE_IMPACT = 0.25
        MAX_OK_IMPACT = 0.6

        # Outcome mapping

        if vs > 12:  # ~2400 ft/min, extreme VS is auto-lethal
            crash(lethal=True)
            return

        if impact_severity <= MAX_SAFE_IMPACT:
            good_landing()
        elif impact_severity <= MAX_OK_IMPACT:
            hard_landing()
        else:
            crash(damage_taken=impact_severity-MAX_OK_IMPACT)

    def update(self, dt: int):
        # Sideways movement - convert roll to yaw
        CONVERSION_FACTOR = 30
        self.rot.y += sin(rad(self.rot.z)) * clamp(self.vel.length()/30.87, (0, 1)) * CONVERSION_FACTOR * dt/1000
        pitch, yaw, *_ = self.rot
        roll = (self.rot.z + 180) % 360 - 180

        # Forward vector (where nose points)
        forward_vec = pg.Vector3(
            sin(rad(yaw)) * cos(rad(pitch)),
            sin(rad(-pitch)),  # pitch is negated since +pitch = nose down
            -cos(rad(yaw)) * cos(rad(pitch)),
        ).normalize()

        # Calculate thrust and weight
        thrust = pg.Vector3(0, 0, 0) if self.disabled else forward_vec * self.throttle_frac*self.model.max_throttle
        weight = pg.Vector3(0, -GRAVITY * self.model.mass, 0)

        # Calculate Angle of Attack (AoA)
        airspeed = self.vel.length()
        if airspeed < EPSILON:
            self.aoa = 0
        else:
            vel_unit_vec = self.vel.normalize()
            # AoA ≈ pitch difference between forward and velocity
            # asin(y-component) gives pitch angle
            pitch_forward = asin(forward_vec.y)        # radians
            pitch_velocity = asin(vel_unit_vec.y)      # radians
            self.aoa = degrees(pitch_forward - pitch_velocity)

        # Calculate lift, using previously calculated airspeed
        if not self.stalling:
            cl = self.model.cl_max * self.aoa/self.model.stall_angle
        else:
            excess = self.aoa - self.model.stall_angle  # degrees
            cl = max(0.125, self.model.cl_max * (1 - 0.1*excess))
        lift_mag = 0.5 * AIR_DENSITY * airspeed**2 * self.model.wing_area * cl

        airflow = -self.vel
        if airflow.length_squared() < EPSILON:
            lift = pg.Vector3(0, 0, 0)
        else:
            airflow_dir = airflow.normalize()

            # Right vector (wing span direction)
            up = pg.Vector3(0, 1, 0)
            right = forward_vec.cross(up).normalize()

            # Lift direction = airflow_dir rotated 90° around right vector
            # Approximate small-angle rotation using cross product:
            lift_dir = airflow_dir.cross(right).normalize()

            # Lift increase from flaps
            lift_mag *= 1 + (1 - self.flaps) * self.model.flap_lift_bonus

            # Lift vector
            lift = lift_dir * lift_mag

        # Calculate drag
        cd = self.model.cd_min + self.model.cd_slope*abs(self.aoa)  # Baseline
        if self.stalling:
            excess = self.aoa - self.model.stall_angle  # degrees
            cd += excess**2 * 0.004  # Stall drag penalty
        if self.pos.y == 0:
            cd *= 1.5  # Extra drag from friction with ground
        cd = min(cd, 1)

        drag_mag = 0.5 * AIR_DENSITY * airspeed**2 * self.model.wing_area * cd

        # Drag increase from flaps
        drag_mag *= 1 + (1 - self.flaps) * self.model.flap_drag_penalty

        if airspeed < EPSILON:
            drag = pg.Vector3(0, 0, 0)
        else:
            drag = -self.vel.normalize() * drag_mag

        if self.braking and self.on_ground:
            drag *= 3

        # Combine and integrate
        net_force = thrust + weight + lift + drag  # Force vector in Newtons
        self.acc = net_force / self.model.mass
        self.vel += self.acc * dt/1000
        self.pos += self.vel * dt/1000

        # Clamp velocity to prevent NaNs
        if self.vel.length() > 1_000:
            self.vel.scale_to_length(1_000)

        # Roll stabilisation
        roll_stability_torque = -roll * self.model.roll_stability_factor
        self.rot_rate.z += roll_stability_torque * dt/1000

        # Yaw torque from rudder
        yaw_torque = self.rudder * self.model.rudder_sensitivity * dt/1000
        self.rot_rate.y += yaw_torque
        self.rot_rate.y *= (1 - 0.8 * dt/1000)

        factor = clamp(1 - abs(self.rot.z)/self.model.max_bank_angle, (0, 1))
        effective_rudder_roll = self.model.rudder_roll_effect * factor  # extra roll from rudder
        if self.on_ground:
            effective_rudder_roll *= 0.2  # mostly suppressed if on ground
        self.rot_rate.z += self.rudder * effective_rudder_roll * dt/1000

        # Clamp and integrate rotation
        self.rot_rate.x = clamp(self.rot_rate.x, (-25, 25))
        self.rot_rate.y = clamp(self.rot_rate.y, (-100, 100))
        self.rot_rate.z = clamp(self.rot_rate.z, (-25, 25))

        self.rot.x += self.rot_rate.x * (1 - abs(self.rot.x / 90)) * dt/1000  # Rotation is slower near top or bottom
        self.rot.y += self.rot_rate.y * dt/1000
        self.rot.z += self.rot_rate.z * dt/1000

        # Stalling
        if self.stalling:
            STALL_DROOP_RATE = 5
            self.rot_rate.x += STALL_DROOP_RATE * dt/1000  # pitch down sharply

        # TODO: Improve AoA calculation
        # AoA should not simply be the pitch difference between velocity and forward vectors

        # Clamp/normalise rotation values
        self.rot.y %= 360
        self.rot.z %= 360
        self.rot.x = clamp(self.rot.x, (-90, 90))

        # Clamp position to prevent going off the map
        self.pos.x = clamp(self.pos.x, (-PRACTISE_LIMIT, PRACTISE_LIMIT))
        self.pos.z = clamp(self.pos.z, (-PRACTISE_LIMIT, PRACTISE_LIMIT))

        # Damage update - damage is proportional to square of excess velocity
        DAMAGE_FACTOR = 0.002
        dp_excess = max(0, self.vel.length()**2 - self.model.v_ne**2)  # represents excess dynamic pressure
        self.damage_level += dt/1000 * DAMAGE_FACTOR * dp_excess

        # TODO: Add damage when not on runway (once runways are added)

        # Collision detection
        GROUND_HEIGHT = self.ground.get_height(self.pos.x, self.pos.z)

        # TODO: for now it's the ground height, but runways should be a factor as well, as well as ocean
        if self.pos.y <= GROUND_HEIGHT:
            self.pos.y = GROUND_HEIGHT

            if not self.on_ground:
                self.process_landing()

            if not self.crashed:
                self.vel.y = max(self.vel.y, 0)  # Plane can't fall through floor
            self.on_ground = True
        else:
            self.on_ground = False

        self.damage_level = clamp(self.damage_level, (0, 1))

class Runway(Entity):
    def __init__(self, x: float, y: float, z: float, width: float, length: float, heading: float = 0):
        super().__init__(x, y, z)
        self.width = width
        self.length = length
        self.heading = heading

    def draw(self):
        gl.glPushMatrix()

        # Enable polygon offset to "pull" the runway towards the camera
        gl.glEnable(gl.GL_POLYGON_OFFSET_FILL)
        gl.glPolygonOffset(-1.0, -1.0)

        # Translate and rotate to runway's position and heading
        gl.glTranslatef(self.pos.x, 0.1 + self.pos.y, self.pos.z)
        gl.glRotatef(self.heading, 0, 1, 0)
        gl.glColor3f(0.2, 0.2, 0.2)

        half_width = self.width / 2
        half_length = self.length / 2

        gl.glBegin(gl.GL_QUADS)
        gl.glVertex3f(-half_width, 0, -half_length)
        gl.glVertex3f(half_width, 0, -half_length)
        gl.glVertex3f(half_width, 0, half_length)
        gl.glVertex3f(-half_width, 0, half_length)
        gl.glEnd()

        # Disable polygon offset
        gl.glDisable(gl.GL_POLYGON_OFFSET_FILL)

        gl.glPopMatrix()