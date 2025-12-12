import pygame as pg
import OpenGL.GL as gl
import OpenGL.GLU as glu
import math

from core.custom_types import Surface, Coord3
from core.constants import (
    GROUND_SIZE, WN_W, WN_H,
    PlaneModel, PLANE_MODEL, AIR_DENSITY
)

# Physics Constants
GRAVITY = 0.00002
DRAG = 0.001
THRUST_FORCE = 0.0005

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

    def update(self, dt: int):
        pass  # TODO: Make my own implementation

        self.rot.y += self.rot.z * 0.05 * dt/1000

        # # --- Orientation vectors ---
        # pitch, yaw, roll = self.rot

        # forward_x = -math.sin(math.radians(yaw)) * math.cos(math.radians(pitch))
        # forward_y =  math.sin(math.radians(pitch))
        # forward_z = -math.cos(math.radians(yaw)) * math.cos(math.radians(pitch))
        # forward = pg.Vector3(forward_x, forward_y, forward_z)
        # if forward.length() > 0:
        #     forward = forward.normalize()

        # # --- Velocity direction ---
        # speed = self.vel.length()
        # if speed > 0.01:
        #     vel_dir = self.vel.normalize()
        # else:
        #     vel_dir = forward

        # # --- Angle of Attack (AoA) ---
        # dot = forward.dot(vel_dir)
        # dot = max(-1.0, min(1.0, dot))   # HARD clamp
        # aoa = math.degrees(math.acos(dot))

        # # Guard against junk AoA when speed is tiny
        # if speed < 1.0:
        #     aoa = 0

        # # --- Lift Coefficient ---
        # if aoa <= STALL_ANGLE:
        #     CL = CL_MAX * (aoa / STALL_ANGLE)
        # else:
        #     CL = max(0.0, CL_MAX * (1 - 0.1 * (aoa - STALL_ANGLE)))

        # # --- Dynamic Pressure ---
        # q = 0.5 * AIR_DENSITY * speed * speed

        # # --- Correct lift direction (perpendicular to airflow) ---
        # up = pg.Vector3(0, 1, 0)
        # # cross twice to get the perpendicular-to-velocity, mostly-up lift vector
        # lift_dir = vel_dir.cross(up).cross(vel_dir)
        # if lift_dir.length() > 0:
        #     lift_dir = lift_dir.normalize()
        # else:
        #     lift_dir = up  # fallback if velocity is vertical

        # lift = lift_dir * (CL * q * WING_AREA)

        # # --- Forces ---
        # thrust = forward * self.throttle * THRUST_FORCE
        # gravity = pg.Vector3(0, -GRAVITY, 0)
        # drag = -self.vel * DRAG

        # # --- Combine & integrate ---
        # self.acc = thrust + gravity + drag + lift
        # self.vel += self.acc * dt
        # self.pos += self.vel * dt

        # if self.pos.y < 0:
        #     self.pos.y = 0
        # if self.vel.y < 0:
        #     self.vel.y = 0

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

        gl.glEnable(gl.GL_TEXTURE_2D)
        gl.glBindTexture(gl.GL_TEXTURE_2D, self.texture_id)
        gl.glColor3f(1.0, 1.0, 1.0) # Ensure no color tint from glColor3f

        gl.glBegin(gl.GL_TRIANGLE_STRIP)
        # Assign texture coordinates (U, V) to each vertex
        # The 10.0 here makes the texture repeat 10 times across the ground plane
        gl.glTexCoord2f(0.0, 0.0); gl.glVertex3f(self.vertices[0][0], self.vertices[0][1], self.vertices[0][2])
        gl.glTexCoord2f(0.0, 10.0); gl.glVertex3f(self.vertices[1][0], self.vertices[1][1], self.vertices[1][2])
        gl.glTexCoord2f(10.0, 0.0); gl.glVertex3f(self.vertices[2][0], self.vertices[2][1], self.vertices[2][2])
        gl.glTexCoord2f(10.0, 10.0); gl.glVertex3f(self.vertices[3][0], self.vertices[3][1], self.vertices[3][2])
        gl.glEnd()

        gl.glDisable(gl.GL_TEXTURE_2D)
        gl.glBindTexture(gl.GL_TEXTURE_2D, 0) # Unbind texture

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