"""camera.py - world (meters) -> screen (pixels) conversion.

Two view modes: "bird" (top-down) and "tilt" (perspective, the
spacetime-fabric look). Zoom, pitch, yaw, and focus are all
live-adjustable at runtime.
"""
import math

import numpy as np


class Camera:
    BIRD = "bird"
    TILT = "tilt"

    MIN_PITCH_DEG, MAX_PITCH_DEG = 12, 85
    MIN_ZOOM, MAX_ZOOM = 0.25, 6.0

    def __init__(self, width, height, scale, pitch_degrees=50, cam_dist=2600,
                 radial_power=0.6):
        self.width = width
        self.height = height
        self.scale = scale          # pixels per meter
        self._default_pitch_degrees = pitch_degrees
        self.pitch = math.radians(pitch_degrees)
        self.cam_dist = cam_dist    # larger -> less perspective distortion
        self.mode = self.TILT
        self.zoom = 1.0
        self.yaw = 0.0
        self.focus_x = 0.0
        self.focus_y = 0.0
        self.focus_z = 0.0
        self.screen_offset_x = 0.0
        self.screen_offset_y = 0.0
        self.radial_power = radial_power
        self.reference_radius = min(width, height) * 0.42

    # ---- live camera controls -------------------------------------------------
    def adjust_zoom(self, factor):
        self.zoom = max(self.MIN_ZOOM, min(self.MAX_ZOOM, self.zoom * factor))

    def adjust_pitch(self, delta_degrees):
        degrees = max(self.MIN_PITCH_DEG,
                       min(self.MAX_PITCH_DEG, math.degrees(self.pitch) + delta_degrees))
        self.pitch = math.radians(degrees)

    def adjust_yaw(self, delta_degrees):
        self.yaw = (self.yaw + math.radians(delta_degrees)) % (2 * math.pi)

    def reset_view(self):
        self.zoom = 1.0
        self.yaw = 0.0
        self.pitch = math.radians(self._default_pitch_degrees)
        

    def set_focus(self, x, y, z=0.0):
        self.focus_x = x
        self.focus_y = y
        self.focus_z = z

    # ---- projection -------------------------------------------------
    def _remap_radial(self, xp, yp):  # Encapsulation
        """Scalar and array cases are handled separately - project()
        calls this per body per trail point per frame, and numpy's
        per-call overhead adds up fast at that scale."""
        if self.radial_power == 1.0:
            return xp, yp
        if isinstance(xp, np.ndarray):
            r = np.hypot(xp, yp)
            r_safe = np.where(r < 1e-6, 1.0, r)
            r_new = self.reference_radius * (r_safe / self.reference_radius) ** self.radial_power
            f = np.where(r < 1e-6, 1.0, r_new / r_safe)
            return xp * f, yp * f
        r = math.hypot(xp, yp)
        if r < 1e-6:
            return xp, yp
        r_new = self.reference_radius * (r / self.reference_radius) ** self.radial_power
        f = r_new / r
        return xp * f, yp * f

    def _apply_yaw(self, xp, yp):  # Encapsulation
        if self.yaw == 0.0:
            return xp, yp
        cos_y, sin_y = math.cos(self.yaw), math.sin(self.yaw)
        return xp * cos_y - yp * sin_y, xp * sin_y + yp * cos_y

    def project(self, position):
        xp = (position.x - self.focus_x) * self.scale * self.zoom
        yp = (position.y - self.focus_y) * self.scale * self.zoom
        zp = (position.z - self.focus_z) * self.scale * self.zoom
        xp, yp = self._remap_radial(xp, yp)
        xp, yp = self._apply_yaw(xp, yp)

        if self.mode == self.BIRD:
            sx, sy = xp + self.width / 2, yp + self.height / 2
        else:
            sx, sy = self._tilt(xp, yp, zp)
        return sx + self.screen_offset_x, sy + self.screen_offset_y

    def project_grid(self, xp, yp, zp):
        """Same as project(), but for whole numpy arrays at once."""
        xp = xp * self.zoom - self.focus_x * self.scale * self.zoom
        yp = yp * self.zoom - self.focus_y * self.scale * self.zoom
        zp = zp * self.zoom
        xp, yp = self._remap_radial(xp, yp)
        xp, yp = self._apply_yaw(xp, yp)

        if self.mode == self.BIRD:
            return xp + self.width / 2, yp + self.height / 2

        return self._tilt(xp, yp, zp)

    def _tilt(self, xp, yp, zp):  # Encapsulation
        cos_p, sin_p = math.cos(self.pitch), math.sin(self.pitch)
        y2 = -yp * cos_p - zp * sin_p
        z2 = yp * sin_p + zp * cos_p
        w = self.cam_dist / (self.cam_dist + z2)
        return xp * w + self.width / 2, y2 * w + self.height / 2
