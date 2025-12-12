import pygame as pg
import OpenGL.GL as gl
import OpenGL.GLU as glu
from math import sin, cos, asin, degrees, radians as rad

from core.custom_types import Surface, Coord3
from core.utils import clamp
from core.constants import (
    GROUND_SIZE, WN_W, WN_H,
    PlaneModel, PLANE_MODEL, AIR_DENSITY, GRAVITY, PRACTISE_LIMIT, EPSILON
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
    def __init__(self):
        super().__init__(0, 0, 0)
        self.model: PlaneModel = PLANE_MODEL

        self.vel: pg.Vector3 = pg.Vector3(0, 0, 0)
        self.acc: pg.Vector3 = pg.Vector3(0, 0, 0)
        self.rot: pg.Vector3 = pg.Vector3(0, 0, 0)  # pitch, yaw, roll

        self.throttle_frac: float = 0
        self.flaps: float = 0

        self.aoa = 0

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
        if self.aoa > self.model.stall_angle:  # Extra drag while stalling
            cd += self.aoa-self.model.stall_angle*0.08  # Extra drag while on ground
        if self.pos.y == 0:
            cd *= 1.25
        cd = min(cd, 1)

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

        # Clamp velocity
        if self.vel.length() > 1000:
            self.vel.scale_to_length(1000)

        # Clamp
        self.pos.x = clamp(self.pos.x, -PRACTISE_LIMIT, PRACTISE_LIMIT)
        self.pos.z = clamp(self.pos.z, -PRACTISE_LIMIT, PRACTISE_LIMIT)

        # Ground collision
        if self.pos.y < 0:
            self.pos.y = 0
            if self.vel.y < 0:
                self.vel.y = 0

class Ground(Entity):
    def __init__(self, image_surface: Surface) -> None:
        super().__init__(0, 0, 0) # Initialize pos for Ground at origin
        self.vertices: list[Coord3] = [
            (-GROUND_SIZE, 0, -GROUND_SIZE),
            (-GROUND_SIZE, 0, GROUND_SIZE),
            (GROUND_SIZE, 0, -GROUND_SIZE),
            (GROUND_SIZE, 0, GROUND_SIZE)
        ]
        self.texture_id = None
        self._load_texture(image_surface)

    def _load_texture(self, image_surface: Surface):
        # OpenGL textures are often Y-flipped compared to Pygame
        image_surface = pg.transform.flip(image_surface, False, True)
        image_data = pg.image.tostring(image_surface, "RGBA", True) # Get pixel data

        # Generate OpenGL texture ID
        self.texture_id = gl.glGenTextures(1)
        gl.glBindTexture(gl.GL_TEXTURE_2D, self.texture_id)

        # Set texture parameters
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_S, gl.GL_REPEAT) # Repeat texture horizontally
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_T, gl.GL_REPEAT) # Repeat texture vertically

        # Upload texture data to OpenGL
        gl.glTexImage2D(gl.GL_TEXTURE_2D, 0, gl.GL_RGBA, image_surface.get_width(), image_surface.get_height(), 0, gl.GL_RGBA, gl.GL_UNSIGNED_BYTE, image_data)
        gl.glBindTexture(gl.GL_TEXTURE_2D, 0) # Unbind texture

    def draw(self): # The `wn` parameter might not be necessary for OpenGL rendering
        gl.glPushMatrix()

        # Enable polygon offset to prevent Z-fighting with other objects on the ground
        gl.glEnable(gl.GL_POLYGON_OFFSET_FILL)
        gl.glPolygonOffset(-1.0, -1.0)

        gl.glEnable(gl.GL_TEXTURE_2D)
        gl.glBindTexture(gl.GL_TEXTURE_2D, self.texture_id)
        gl.glColor3f(1.0, 1.0, 1.0) # Ensure no color tint from glColor3f

        gl.glBegin(gl.GL_TRIANGLE_STRIP)
        # Assign texture coordinates (U, V) to each vertex
        # The 10.0 here makes the texture repeat 10 times across the ground plane
        texture_repeat_count = 1000  # Make texture repeat many times over large ground
        gl.glTexCoord2f(0.0, 0.0); gl.glVertex3f(self.vertices[0][0], self.vertices[0][1], self.vertices[0][2])
        gl.glTexCoord2f(0.0, texture_repeat_count); gl.glVertex3f(self.vertices[1][0], self.vertices[1][1], self.vertices[1][2])
        gl.glTexCoord2f(texture_repeat_count, 0.0); gl.glVertex3f(self.vertices[2][0], self.vertices[2][1], self.vertices[2][2])
        gl.glTexCoord2f(texture_repeat_count, texture_repeat_count); gl.glVertex3f(self.vertices[3][0], self.vertices[3][1], self.vertices[3][2])
        gl.glEnd()

        gl.glDisable(gl.GL_TEXTURE_2D)
        gl.glBindTexture(gl.GL_TEXTURE_2D, 0) # Unbind texture

        # Disable polygon offset after drawing the ground
        gl.glDisable(gl.GL_POLYGON_OFFSET_FILL)

        gl.glPopMatrix()

class Sky(Entity):
    def __init__(self) -> None:
        super().__init__(0, 0, 0) # Sky is at origin

    def draw(self, colour_scheme) -> None:
        gl.glMatrixMode(gl.GL_PROJECTION)
        gl.glPushMatrix()
        gl.glLoadIdentity()
        glu.gluOrtho2D(0, WN_W, WN_H, 0)
        gl.glMatrixMode(gl.GL_MODELVIEW)
        gl.glPushMatrix()
        gl.glLoadIdentity()

        gl.glDisable(gl.GL_DEPTH_TEST)
        gl.glBegin(gl.GL_QUADS)
        # Top half (high to mid)
        gl.glColor3ub(*colour_scheme.high)
        gl.glVertex2f(0, 0)
        gl.glVertex2f(WN_W, 0)
        gl.glColor3ub(*colour_scheme.mid)
        gl.glVertex2f(WN_W, WN_H / 2)
        gl.glVertex2f(0, WN_H / 2)
        # Bottom half (mid to low)
        gl.glColor3ub(*colour_scheme.mid)
        gl.glVertex2f(0, WN_H / 2)
        gl.glVertex2f(WN_W, WN_H / 2)
        gl.glColor3ub(*colour_scheme.low)
        gl.glVertex2f(WN_W, WN_H)
        gl.glVertex2f(0, WN_H)
        gl.glEnd()
        gl.glEnable(gl.GL_DEPTH_TEST)

        gl.glPopMatrix()
        gl.glMatrixMode(gl.GL_PROJECTION)
        gl.glPopMatrix()
        gl.glMatrixMode(gl.GL_MODELVIEW)