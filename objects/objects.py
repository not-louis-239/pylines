"""General purpose module in which to place simulation objects."""

import pygame as pg
import OpenGL.GL as gl
import OpenGL.GLU as glu
from math import sin, cos, asin, degrees, radians as rad

from core.asset_manager import Sounds
from core.custom_types import Surface, Coord3
from core.utils import clamp
from core.constants import (
    GROUND_SIZE, WN_W, WN_H,
    PlaneModel, PLANE_MODELS, AIR_DENSITY, GRAVITY, PRACTISE_LIMIT, EPSILON
)

class Entity:
    """Mental basis for all in-game physical objects"""

    def __init__(self, x: float, y: float, z: float) -> None:
        self.pos: pg.Vector3 = pg.Vector3(x, y, z)

    def update(self, dt):
        pass

    def draw(self, wn: Surface):
        pass

class Plane(Entity):
    def __init__(self, sounds: Sounds):
        super().__init__(0, 0, 0)
        self.model: PlaneModel = PLANE_MODELS["Cessna 172"]

        self.vel: pg.Vector3 = pg.Vector3(0, 0, 0)
        self.acc: pg.Vector3 = pg.Vector3(0, 0, 0)
        self.rot: pg.Vector3 = pg.Vector3(0, 0, 0)  # pitch, yaw, roll

        self.throttle_frac: float = 0
        self.flaps: float = 0

        self.sounds = sounds
        self.aoa = 0

        self.on_ground = True
        self.crash_reason: str | None = None

    @property
    def crashed(self) -> bool:
        return self.crash_reason is not None

    def reset(self) -> None:
        self.pos = pg.Vector3(0, 0, 0)
        self.vel = pg.Vector3(0, 0, 0)
        self.acc = pg.Vector3(0, 0, 0)

        self.throttle_frac = 0
        self.rot = pg.Vector3(0, 0, 0)
        self.show_stall_warning: bool = False

        self.aoa = 0
        self.on_ground = True
        self.flaps = 0
        self.crash_reason = None

    def check_landing(self):
        # Check landing for quality
        pitch, yaw, roll = self.rot
        roll = (roll+180)%360 - 180  # Normalise

        landing_good = self.vel.y > -1.7 and abs(roll) < 5 and -pitch > -12
        landing_passable = self.vel.y > -4 and abs(roll) < 30 and -pitch > -20

        if landing_good:
            self.sounds.good_landing.play()
        elif landing_passable:
            self.sounds.hard_landing.play()
        else:
            self.sounds.crash.play()
            self.crash_reason = 'ground'

    def update(self, dt: int):
        # Sideways movement - convert roll to yaw
        self.rot.y += sin(rad(self.rot.z)) * 30 * dt/1000 * self.throttle_frac

        # Pitch, yaw, roll
        pitch, yaw, roll = self.rot

        # Forward vector (where the nose points)
        forward_vec = pg.Vector3(
            sin(rad(yaw)) * cos(rad(pitch)),
            sin(rad(-pitch)),  # pitch is negated since +pitch = nose down
            -cos(rad(yaw)) * cos(rad(pitch)),
        ).normalize()

        # Calculate thrust and weight
        thrust = forward_vec * self.throttle_frac*self.model.max_throttle
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

        # Calculate lift, using the previously calculated airspeed
        if self.aoa < self.model.stall_angle:
            cl = self.model.cl_max * self.aoa/self.model.stall_angle
        else:
            cl = max(0, self.model.cl_max - (self.aoa-self.model.stall_angle)*0.2)
        lift_mag = 0.5 * AIR_DENSITY * airspeed**2 * self.model.wing_area * cl

        airflow = -self.vel
        if airflow.length_squared() < EPSILON:
            lift = pg.Vector3(0, 0, 0)
        else:
            airflow_dir = airflow.normalize()

            # Right vector (wing span direction)
            up = pg.Vector3(0, 1, 0)
            right = forward_vec.cross(up).normalize()

            # 3. Lift direction = airflow_dir rotated 90° around right vector
            # Approximate small-angle rotation using cross product:
            lift_dir = airflow_dir.cross(right).normalize()

            # 4. Lift vector
            lift = lift_dir * lift_mag

        # Calculate drag
        cd = self.model.cd_min + self.model.cd_slope*abs(self.aoa)  # Baseline
        if self.aoa > self.model.stall_angle:
            cd += (self.aoa-self.model.stall_angle)*0.012  # Stall drag penalty
        if self.pos.y == 0:
            cd *= 1.5  # Extra drag from friction with ground
        cd = min(cd, 0.5)
        cd = 0  # DEBUG

        drag_mag = 0.5 * AIR_DENSITY * airspeed**2 * self.model.wing_area * cd

        if airspeed < EPSILON:
            drag = pg.Vector3(0, 0, 0)
        else:
            drag = -self.vel.normalize() * drag_mag

        # Combine forces
        net_force = thrust + weight + lift + drag  # Force vector in Newtons
        self.acc = net_force / self.model.mass

        # Integrate
        self.vel += self.acc * dt/1000
        self.pos += self.vel * dt/1000

        # Clamp velocity to prevent NaNs
        if self.vel.length() > 1_000:
            self.vel.scale_to_length(1_000)

        # Clamp
        self.pos.x = clamp(self.pos.x, -PRACTISE_LIMIT, PRACTISE_LIMIT)
        self.pos.z = clamp(self.pos.z, -PRACTISE_LIMIT, PRACTISE_LIMIT)

        # Ground collision
        if self.pos.y <= 0:
            self.pos.y = 0

            if not self.on_ground:  # Only check transition from air -> ground
                self.check_landing()

            if not self.crashed:
                self.vel.y = max(self.vel.y, 0)  # Plane can't fall through floor
            self.on_ground = True
        else:
            self.on_ground = False

class Runway(Entity): ...  # TODO