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

"""General purpose module in which to place simulation objects."""
from __future__ import annotations

from enum import Enum
from math import asin, atan2, cos, degrees, sin
from math import radians as rad
import random
from typing import TYPE_CHECKING

import pygame as pg

import pylines.core.constants as C
from pylines.core.asset_manager import Sounds
from pylines.core.collision_checkers import (
    point_in_cuboid,
    point_in_cylinder,
    point_in_sphere,
)
from pylines.core.custom_types import Surface
from pylines.core.utils import clamp, point_in_aabb, rotate_around_axis, get_sign
from pylines.objects.building_parts import Primitive
from pylines.objects.rotation_input_container import RotationInputContainer

if TYPE_CHECKING:
    from pylines.game.environment import Environment
    from pylines.game.screens.game_screen import DialogMessage

_global_up: pg.Vector3 = pg.Vector3(0, 1, 0)  # world up

class CrashReason(Enum):
    TERRAIN = "terrain"
    OBSTACLE = "building"
    OCEAN = "ocean"
    RUNWAY = "runway"  # reserved for fatal improper landing on runway, e.g. excessive sink rate, bad attitude

class Entity:
    """Base class for all in-game physical or contrallable objects."""

    def __init__(self, x: float, y: float, z: float) -> None:
        self.pos: pg.Vector3 = pg.Vector3(x, y, z)

    def update(self, dt):
        pass

    def draw(self, wn: Surface):
        pass

class Plane(Entity):
    def __init__(self, sounds: Sounds, dialog_box: DialogMessage, env: Environment, rot_input_container: RotationInputContainer):
        super().__init__(0, 0, 0)
        self.model: C.PlaneModel = C.PLANE_MODELS["Cessna 172"]
        self.sounds = sounds
        self.dialog_box = dialog_box
        self.env = env
        self.time_since_lethal_crash: float | None = None  # None = hasn't crashed yet, used for explosion animation
        self.rot_input_container = rot_input_container
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
    def stalled(self) -> bool:
        return self.aoa > self.model.stall_angle

    @property
    def over_runway(self) -> bool:
        x, _, z = self.pos

        for runway in self.env.runways:
            rx, _, rz = runway.pos
            rl, rw = runway.l, runway.w

            # FIXME: don't ask me why I have to swap the length and width around

            inside, _ = point_in_aabb(x, z, rx, rz, rw, rl, runway.heading)
            if inside:
                return True

        return False

    def reset(self) -> None:
        STARTING_POS = (200, -3_000)
        STARTING_YAW_DEGREES = 310

        sx, sz = STARTING_POS
        self.pos = pg.Vector3(sx, self.env.height_at(sx, sz), sz)
        self.vel = pg.Vector3(0, 0, 0)
        self.acc = pg.Vector3(0, 0, 0)

        self.throttle_frac: float = 0  # from 0 to 1
        self.flaps: float = 0.7  # 0 = down, 1 = up, flaps start slightly down for takeoff
        self.rudder: float = 0  # from -1 to 1 (deflection)
        self.braking = False

        self.show_stall_warning: bool = False

        # Using a native forward vector for rotation makes rotating around local axes easier
        self.native_fwd: pg.Vector3 = pg.Vector3(
            sin(rad(STARTING_YAW_DEGREES)),
            0,
            -cos(rad(STARTING_YAW_DEGREES))
        )
        self.native_up: pg.Vector3 = pg.Vector3(0, 1, 0)  # Can be assumed world up as plane starts horizontal

        self.rot_rate = pg.Vector3(0, 0, 0)  # pitch, yaw, roll rates in degrees per second, applied relative to local axes
        self.aoa = 0  # degrees
        self.on_ground = True

        # Reset crash/damage metrics
        self.crash_reason: CrashReason | None = None
        self.time_since_lethal_crash = None
        self.damage_level = 0

    @property
    def native_right(self) -> pg.Vector3:
        return self.native_fwd.cross(self.native_up).normalize()

    def get_rot(self) -> tuple[float, float, float]:
        """Returns a tuple where x=pitch, y=yaw, z=roll, each in degrees."""

        return (
            -degrees(asin(clamp(self.native_fwd.y, (-1, 1)))),  # pitch
            degrees(atan2(self.native_fwd.x, -self.native_fwd.z)),  # yaw
            degrees(atan2(self.native_right.y, self.native_up.y))  # roll
        )

    def increment_crash_timer(self, dt: int) -> None:
        assert self.time_since_lethal_crash is not None, "Cannot increment if crash hasn't happened"
        self.time_since_lethal_crash += dt/1000  # convert ms to seconds

    def good_landing(self):
        self.sounds.good_landing.play()
        self.dialog_box.set_message("Good landing!", (0, 255, 0))

    def hard_landing(self, *, suppress_dialog: bool = False):
        self.sounds.hard_landing.play()
        if not suppress_dialog: self.dialog_box.set_message("Hard landing...", (255, 200, 0))

    def crash(self, *, reason: CrashReason, suppress_dialog: bool = False, damage_taken: float = 0.0, lethal: bool = False):
        self.damage_level = 1 if lethal else min(self.damage_level + damage_taken, 1)

        if self.damage_level >= 1:
            # Lethal crash that renders plane completely unflyable
            self.sounds.crash.play()
            self.time_since_lethal_crash = 0  # start timer
            self.crash_reason = reason
        else:
            # Damaging but non-fatal crash
            self.sounds.hard_landing.play()
            if not suppress_dialog: self.dialog_box.set_message("Hard landing. Damage sustained.", (255, 80, 0))

    def calculate_aoa(self) -> float:
        """Returns Angle of Attack (AoA) in degrees, calculated
        as the signed angle between the plane's forward vector and its
        velocity vector.

        A positive result means the nose is above the velocity vector
        (nose-up AoA); negative means the nose is below (nose-down).
        """

        if self.vel.length() < C.MATH_EPSILON:
            return 0  # Default fallback AoA when stationary

        vel_unit = self.vel.normalize()

        # dot product for cosine, cross magnitude for sine
        dot = clamp(self.native_fwd.dot(vel_unit), (-1, 1))
        cross = self.native_fwd.cross(vel_unit)

        # Determine sign using the aircraft's right-hand axis
        sign = get_sign(cross.dot(self.native_right))
        # get_sign returns 1, 0 or -1 based on the sign of
        # the input, so AoA will be exactly 0 if velocity
        # is perfectly aligned with forward vector, which
        # is a nice property to have

        # atan2 handles the full angle range and avoids domain issues
        angle = atan2(cross.length(), dot)
        return -sign * degrees(angle)

    def process_landing(self):
        if self.crashed:
            return

        # Reset landing sounds
        self.sounds.good_landing.stop()
        self.sounds.hard_landing.stop()
        self.sounds.crash.stop()

        # Check landing for quality
        pitch, _, roll = self.get_rot()
        roll = (roll+180)%360 - 180  # Normalise

        # Safety parameters
        SAFE_VS = 1.7  # m/s
        MAX_OK_VS = 4
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

        # Determine reason
        water_crash = self.pos.y < self.env.sea_level + C.MATH_EPSILON
        if water_crash:
            crash_reason = CrashReason.OCEAN
        elif self.over_runway:
            crash_reason = CrashReason.RUNWAY
        else:
            crash_reason = CrashReason.TERRAIN

        # Outcome mapping
        if vs > 12 or water_crash:
            self.crash(lethal=True, reason=crash_reason)
            return

        if impact_severity <= MAX_SAFE_IMPACT:
            if self.over_runway:
                self.good_landing()
            else:
                self.hard_landing(suppress_dialog=True)
        elif impact_severity <= MAX_OK_IMPACT:
            self.hard_landing(suppress_dialog=(not self.over_runway))
        else:
            self.crash(damage_taken=impact_severity-MAX_OK_IMPACT, reason=crash_reason)

    def process_input(self, dt: int):
        dt_seconds = dt / 1000

        BASE_ROT_ACCEL = 40
        control_authority = 1 - 0.875 * self.damage_level**2  # reduce authority based on damage level
        speed_authority_factor = clamp((self.vel.length()/30.87)**2, (0.01, 1))  # based on vel in m/s, higher vel = more authority, with full authority at 30.87 m/s (60 knots)

        # If stalled, controls are weaker
        if not self.stalled:
            stall_authority_penalty = 0
        else:
            excess_aoa = self.aoa - self.model.stall_angle
            stall_severity = clamp(excess_aoa / 30, (0, 1))
            stall_authority_penalty = 0.5 * stall_severity  # up to 50% reduction in control authority at extreme stall

        rot_accel = (1 - stall_authority_penalty) * control_authority * BASE_ROT_ACCEL * speed_authority_factor * (0.2 if self.on_ground else 1) * dt_seconds  # If on ground -> significantly reduces turn authority

        # Update control inputs from input container
        self.rot_rate.x += self.rot_input_container.pitch_input * rot_accel
        self.rot_rate.z -= self.rot_input_container.roll_input * rot_accel

    def update(self, dt: int):
        dt_seconds = dt / 1000

        # Building collision checks
        COLLISION_CULL_RADIUS = 125  # skip building parts too far away to potentially collide

        for building in self.env.buildings:
            COLLISION_BUFFER = 4.0  # account for height gaps, prevent phasing
            # This acts as a "hitbox" for the plane, even though it affects
            # only building dimensions

            for part in building.parts:
                # Calculate the part's absolute world position
                part_world_pos_tuple = (
                    building.pos.x + part.offset.x,
                    building.pos.y + part.offset.y,
                    building.pos.z + part.offset.z
                )

                part_world_pos_vec = pg.Vector3(part_world_pos_tuple)
                if (part_world_pos_vec - self.pos).length() > COLLISION_CULL_RADIUS:
                    continue  # skip over far away building parts for performance

                collided = False
                if part.primitive == Primitive.CUBOID:
                    l, h, w = part.dims
                    cuboid_center = part_world_pos_tuple
                    cuboid_dims = (l, h, w)

                    collided = point_in_cuboid(
                        (self.pos.x, self.pos.y, self.pos.z),
                        cuboid_center,
                        (cuboid_dims[0] + COLLISION_BUFFER*2, cuboid_dims[1] + COLLISION_BUFFER*2, cuboid_dims[2] + COLLISION_BUFFER*2)
                    )
                elif part.primitive == Primitive.CYLINDER:
                    r, h = part.dims
                    cylinder_center = part_world_pos_tuple
                    collided = point_in_cylinder(
                        (self.pos.x, self.pos.y, self.pos.z),
                        cylinder_center,
                        r + COLLISION_BUFFER, h + COLLISION_BUFFER*2
                    )
                elif part.primitive == Primitive.SPHERE:
                    r = part.dims[0]
                    sphere_center = part_world_pos_tuple
                    collided = point_in_sphere(
                        (self.pos.x, self.pos.y, self.pos.z),
                        sphere_center,
                        r + COLLISION_BUFFER
                    )

                if collided:
                    self.crash(lethal=True, reason=CrashReason.OBSTACLE)
                    return

        # Slowly blend velocity towards forward vector to prevent
        # sideslip. This also makes turning easier at low speeds
        airspeed = self.vel.length()  # This should be used all the way through Plane.update() to avoid wasteful recalculation
        if airspeed > C.MATH_EPSILON:
            # compute target velocity aligned with nose
            target_vel = self.native_fwd * airspeed

            # blending factor: stronger at lower speeds, weaker at high speeds
            align_factor = clamp(5.0 / (airspeed + 1e-6), (0, 1))

            # blend
            self.vel = self.vel.lerp(target_vel, align_factor * dt_seconds)

        # Calculate thrust and weight force vectors
        thrust: pg.Vector3 = pg.Vector3(0, 0, 0) if self.disabled else self.native_fwd * self.throttle_frac * self.model.max_throttle
        weight: pg.Vector3 = pg.Vector3(0, -C.GRAVITY * self.model.mass, 0)

        # Calculate Angle of Attack (AoA)
        self.aoa = self.calculate_aoa()

        # Calculate lift, using previously calculated airspeed
        if not self.stalled:
            cl = self.model.cl_max * self.aoa/self.model.stall_angle
        else:
            # Stalling results in lift loss, modelled here as a sharp drop in cl after
            # stall angle is exceeded, with a small amount of residual lift that
            # degrades gradually as AoA increases further beyond stall angle
            excess = self.aoa - self.model.stall_angle  # degrees
            cl = max(0.125, self.model.cl_max * (1 - 0.1*excess))
        lift_mag = 0.5 * C.AIR_DENSITY * airspeed**2 * self.model.wing_area * cl

        airflow = -self.vel  # airflow is a vector opposite the velocity of the plane
        flaps_deflection = 1 - self.flaps  # flap deflection

        if airflow.length_squared() < C.MATH_EPSILON:
            lift = pg.Vector3(0, 0, 0)  # fallback
        else:
            airflow_dir = airflow.normalize()

            # Lift direction = airflow_dir rotated 90° around right vector
            # Approximate small-angle rotation using cross product:
            lift_dir = airflow_dir.cross(self.native_right).normalize()

            # Lift increase from flaps
            lift_mag *= 1 + (flaps_deflection**0.7) * self.model.flap_lift_bonus

            # Lift vector
            lift = lift_dir * lift_mag

        # Calculate drag
        cd = self.model.cd_min + self.model.cd_slope*abs(self.aoa)  # Baseline
        if self.stalled:
            excess = self.aoa - self.model.stall_angle  # degrees
            cd += excess**2 * 0.004  # Stall drag penalty
        if self.pos.y == 0:
            cd *= 1.5  # Extra drag from friction with ground
        cd = min(cd, 1)  # clamp drag to avoid insane values at high AoA

        drag_mag = 0.5 * C.AIR_DENSITY * airspeed**2 * self.model.wing_area * cd

        # Drag increase from flaps
        drag_mag *= 1 + (flaps_deflection**1.8) * self.model.flap_drag_penalty

        if airspeed < C.MATH_EPSILON:
            drag = pg.Vector3(0, 0, 0)
        else:
            drag = -self.vel.normalize() * drag_mag

        if self.braking and self.on_ground:
            self.vel *= (1 - 0.4 * dt_seconds)  # simulated extra friction from braking, 40% per second at full brake

        # World edge boundary
        cheb_dist = max(abs(self.pos.x), abs(self.pos.z))  # Chebyshev distance of plane from origin
        if cheb_dist > C.SOFT_TRAVEL_LIMIT:
            strength_frac = (cheb_dist - C.SOFT_TRAVEL_LIMIT) / (C.HARD_TRAVEL_LIMIT - C.SOFT_TRAVEL_LIMIT)  # 0 to 1, no clamping needed as hard wall exists anyway

            FULL_STRENGTH_ACCEL = self.model.max_throttle/self.model.mass  # m/s² acceleration, cancels out throttle fully at world boundary
            full_strength_force_mag: float = self.model.mass * FULL_STRENGTH_ACCEL  # F = ma
            boundary_bias_mag = full_strength_force_mag * strength_frac ** 2  # superlinear scaling

            vec_to_origin = pg.Vector3(-self.pos.x, 0, -self.pos.z).normalize()  # vector pointing to map origin from plane pos

            # Push plane to origin if it is very far out, to prevent it
            # from going off the map. This is a "soft" boundary
            # that becomes stronger the further out you go, until a hard
            # boundary at C.HARD_TRAVEL_LIMIT that you simply cannot cross.
            boundary_bias = vec_to_origin * boundary_bias_mag
        else:
            boundary_bias = pg.Vector3(0, 0, 0)

        # Combine and integrate forces: F = ma -> a = F/m, then integrate acceleration to velocity and velocity to position
        net_force = thrust + weight + lift + drag + boundary_bias  # Force vectors in Newtons

        self.acc = net_force / self.model.mass  # a = F/m
        self.vel += self.acc * dt_seconds
        self.pos += self.vel * dt_seconds

        # Clamp height
        ground_height = self.env.get_ground_height(self.pos.x, self.pos.z)
        self.pos.y = max(self.pos.y, ground_height)

        # Clamp velocity to prevent NaNs
        if self.vel.length() > 1000:
            self.vel.scale_to_length(1000)

        # Get rotation values
        self.process_input(dt)
        _, _, roll = self.get_rot()

        # Convert roll to yaw over time
        CONVERSION_FACTOR = 1.5
        self.rot_rate.y += roll * CONVERSION_FACTOR * dt_seconds

        # Roll stabilisation - pushes bank towards zero over time
        if -90 <= roll <= 90:
            # Normal flight - push to 0°
            roll_stability_torque = -roll * self.model.roll_stability_factor
        else:
            # Inverted flight - push to ±180°
            if roll < -90:
                roll_stability_torque = (-180 - roll) * self.model.roll_stability_factor
            else:
                roll_stability_torque = (180 - roll) * self.model.roll_stability_factor

        self.rot_rate.z += roll_stability_torque * dt_seconds

        # Yaw torque from rudder - this is what actually makes the rudder "work"
        yaw_torque = self.rudder * self.model.rudder_sensitivity * dt_seconds
        self.rot_rate.y += yaw_torque
        YAW_FRICTION = 1.5
        self.rot_rate.y *= (1 - YAW_FRICTION * dt_seconds)

        # Small amount of extra roll from rudder
        factor = clamp(1 - abs(roll)/self.model.max_bank_angle, (0, 1))
        effective_rudder_roll = self.model.rudder_roll_effect * factor
        if self.on_ground:
            effective_rudder_roll *= 0.2  # mostly suppressed if on ground
        self.rot_rate.z += self.rudder * effective_rudder_roll * dt_seconds

        # Clamp rotation to avoid insane rates
        self.rot_rate.x = clamp(self.rot_rate.x, (-45, 45))
        self.rot_rate.y = clamp(self.rot_rate.y, (-100, 100))
        self.rot_rate.z = clamp(self.rot_rate.z, (-45, 45))

        # Stalling
        if self.stalled:
            # Calculate stall severity based on how much AoA exceeds stall angle
            excess_aoa = self.aoa - self.model.stall_angle
            stall_severity = clamp(excess_aoa / 30, (0, 1))  # from 0 to 1, with 30° AoA excess being max severity

            # Nose wants to pitch downwards
            STALL_PITCH_RATE = 30  # degrees per second^2, nose down
            self.rot_rate.x += STALL_PITCH_RATE * dt_seconds * stall_severity

            # Wing drop - increase roll dramatically in its current direction
            STALL_ROLL_RATE = 30  # degrees per second^2, max roll

            if abs(roll) < C.MATH_EPSILON:
                roll_dir = random.choice([-1, 1])  # If not already rolling, randomly choose a direction to roll
            else:
                roll_dir = get_sign(roll)  # Otherwise, roll in the current direction

            assert roll_dir in (-1, 1), f"Invalid roll direction: {roll_dir}"
            self.rot_rate.z += roll_dir * STALL_ROLL_RATE * dt_seconds * stall_severity
            # This can turn into a spin if not corrected quickly,
            # adding to the challenge of stall recovery

        # Input stabilisation
        if not self.rot_input_container.pitch_input:
            self.rot_rate.x *= (1 - 0.8) ** dt_seconds
        if not self.rot_input_container.roll_input:
            self.rot_rate.z *= (1 - 0.8) ** dt_seconds

        # Apply rotation rates to native forward and up vectors
        self.native_fwd = rotate_around_axis(self.native_fwd, self.native_right, -rad(self.rot_rate.x * dt_seconds))  # pitch
        self.native_fwd = rotate_around_axis(self.native_fwd, self.native_up, -rad(self.rot_rate.y * dt_seconds))  # yaw

        # Apply roll, which updates only the native up vector
        self.native_up = rotate_around_axis(self.native_up, self.native_fwd, rad(self.rot_rate.z * dt_seconds))

        # Re-orthogonalise forward and up vectors to prevent drift over time from
        # floating point imprecision, which would cause gradual distortion of
        # the plane's local axes and weird rotation behaviour
        self.native_fwd = self.native_fwd.normalize()
        self.native_up = (self.native_up - self.native_fwd *
        self.native_up.dot(self.native_fwd)).normalize()

        assert 1 - C.MATH_EPSILON < self.native_fwd.length() < 1 + C.MATH_EPSILON, f"Forward vector not normalised: length={self.native_fwd.length()}"
        assert 1 - C.MATH_EPSILON < self.native_up.length() < 1 + C.MATH_EPSILON, f"Up vector not normalised: length={self.native_up.length()}"
        assert 1 - C.MATH_EPSILON < self.native_right.length() < 1 + C.MATH_EPSILON, f"Right vector not normalised: length={self.native_right.length()}"

        # Clamp position to prevent going off the map - this is the hard travel boundary
        self.pos.x = clamp(self.pos.x, (-C.HARD_TRAVEL_LIMIT, C.HARD_TRAVEL_LIMIT))
        self.pos.z = clamp(self.pos.z, (-C.HARD_TRAVEL_LIMIT, C.HARD_TRAVEL_LIMIT))

        # Damage update - damage is proportional to square of excess velocity
        DAMAGE_FACTOR = 0.0008
        dp_excess = max(0, self.vel.length()**2 - self.model.v_ne**2)  # represents excess dynamic pressure
        self.damage_level += dt_seconds * DAMAGE_FACTOR * dp_excess

        # Collision detection with ground
        ground_height = self.env.get_ground_height(self.pos.x, self.pos.z)
        if self.pos.y <= ground_height:
            # Only process landing if just touched down
            if not self.on_ground:
                self.process_landing()

            self.on_ground = True
            self.pos.y = ground_height

            if not self.over_runway:
                self.vel *= 0.85 ** (dt_seconds)
                self.damage_level += clamp(self.vel.length() / 30, (0, 1))**2 * 0.2 * dt_seconds  # 30 m/s - max terrain scrape damage

            if not self.crashed:
                self.vel.y = 0
        else:
            self.on_ground = False

        self.damage_level = clamp(self.damage_level, (0, 1))
