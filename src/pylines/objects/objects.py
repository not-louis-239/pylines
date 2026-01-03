"""General purpose module in which to place simulation objects."""
from __future__ import annotations
from typing import TYPE_CHECKING
from math import asin, cos, degrees
from math import radians as rad
from math import sin

import OpenGL.GL as gl
import pygame as pg

from pylines.core.asset_manager import Sounds
from pylines.core.constants import (AIR_DENSITY, EPSILON, GRAVITY, PLANE_MODELS, PRACTISE_LIMIT, PlaneModel)
from pylines.core.custom_types import Surface
from pylines.core.utils import clamp

if TYPE_CHECKING:
    from pylines.game.screens.game_screen import DialogMessage

class Entity:
    """Mental basis for all in-game physical objects"""

    def __init__(self, x: float, y: float, z: float) -> None:
        self.pos: pg.Vector3 = pg.Vector3(x, y, z)

    def update(self, dt):
        pass

    def draw(self, wn: Surface):
        pass

class Plane(Entity):
    def __init__(self, sounds: Sounds, dialog_box: DialogMessage):
        super().__init__(0, 0, 0)
        self.model: PlaneModel = PLANE_MODELS["Cessna 172"]
        self.sounds = sounds
        self.dialog_box = dialog_box
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

    @property  # TODO: unused method, integrate where useful
    def stalling(self) -> bool:
        return self.aoa > self.model.stall_angle

    def reset(self) -> None:
        self.pos = pg.Vector3(0, 0, 0)
        self.vel = pg.Vector3(0, 0, 0)
        self.acc = pg.Vector3(0, 0, 0)

        self.throttle_frac: float = 0  # from 0 to 1
        self.flaps: float = 0

        self.rot = pg.Vector3(0, 0, 0)  # pitch, yaw, roll
        self.rot_rate = pg.Vector3(0, 0, 0)
        self.show_stall_warning: bool = False

        self.aoa = 0  # degrees
        self.on_ground = True
        self.flaps = 0
        self.crash_reason = None
        self.damage_level = 0

    def process_landing(self):
        # Check landing for quality
        pitch, yaw, roll = self.rot
        roll = (roll+180)%360 - 180  # Normalise

        landing_good = self.vel.y > -1.7 and abs(roll) < 5 and -pitch > -12
        landing_passable = self.vel.y > -4 and abs(roll) < 30 and -pitch > -20

        if landing_good:
            self.sounds.good_landing.play()
            self.dialog_box.set_message("Good landing!", (0, 255, 0))
        elif landing_passable:
            self.sounds.hard_landing.play()
            self.dialog_box.set_message("Oops... hard landing.", (255, 200, 0))
        else:
            self.sounds.crash.play()
            self.crash_reason = 'ground'
            self.damage_level = 1  # Instant death if crash  # TODO: Should depend on excess velocity

    def update(self, dt: int):
        # Sideways movement - convert roll to yaw
        self.rot.y += sin(rad(self.rot.z)) * 30 * dt/1000 * self.throttle_frac

        pitch, yaw, roll = self.rot

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
        if self.aoa < self.model.stall_angle:
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

        if airspeed < EPSILON:
            drag = pg.Vector3(0, 0, 0)
        else:
            drag = -self.vel.normalize() * drag_mag

        # Combine and integrate
        net_force = thrust + weight + lift + drag  # Force vector in Newtons
        self.acc = net_force / self.model.mass
        self.vel += self.acc * dt/1000
        self.pos += self.vel * dt/1000

        # Clamp velocity to prevent NaNs
        if self.vel.length() > 1_000:
            self.vel.scale_to_length(1_000)

        # Rotation
        self.rot_rate.x = clamp(self.rot_rate.x, (-1, 1))  # TODO: make clamping dt-dependent
        self.rot_rate.z = clamp(self.rot_rate.z, (-5, 5))
        self.rot.x += self.rot_rate.x * (1 - abs(self.rot.x / 90))
        self.rot.z += self.rot_rate.z

        # Stalling
        if self.stalling:
            self.rot_rate.x += 3 * dt/1000

        # TODO: make AoA calculation more accurate

        # Clamp rotation values
        self.rot.y %= 360
        self.rot.z %= 360
        self.rot.x = clamp(self.rot.x, (-90, 90))

        # Clamp position
        self.pos.x = clamp(self.pos.x, (-PRACTISE_LIMIT, PRACTISE_LIMIT))
        self.pos.z = clamp(self.pos.z, (-PRACTISE_LIMIT, PRACTISE_LIMIT))

        # Damage update
        if self.vel.length() > self.model.v_ne:
            self.damage_level += 0.15 * dt/1000

        # TODO: Overspeed damage should depend on excess
        # TODO: Add damage when not on runway (once runways are added)

        # Ground collision
        if self.pos.y <= 0:
            self.pos.y = 0

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
        # TODO: fix runway z-fighting with ground

        gl.glPushMatrix()

        # Translate and rotate to runway's position and heading
        gl.glTranslatef(self.pos.x, self.pos.y + 0.1, self.pos.z)  # y-offset prevents z-fighting
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

        gl.glPopMatrix()