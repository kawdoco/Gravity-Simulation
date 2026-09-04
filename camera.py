import math

import numpy as np


class Camera:
    BIRD = "bird"
    TILT = "tilt"

    def __init__(self, width, height, scale, pitch_degrees=50, cam_dist=2600,
                 radial_power=0.6):
        self.width = width
        self.height = height
        self.scale = scale          # pixels per meter
        self.pitch = math.radians(pitch_degrees)
        self.cam_dist = cam_dist    # larger -> less perspective distortion
        self.mode = self.TILT
        self.radial_power = radial_power
        self.reference_radius = min(width, height) * 0.42

    def toggle(self):
        self.mode = self.BIRD if self.mode == self.TILT else self.TILT

    def _remap_radial(self, xp, yp):  # Encapsulation
        if self.radial_power == 1.0:
            return xp, yp
        r = np.hypot(xp, yp)
        r_safe = np.where(r < 1e-6, 1.0, r)
        r_new = self.reference_radius * (r_safe / self.reference_radius) ** self.radial_power
        f = np.where(r < 1e-6, 1.0, r_new / r_safe)
        return xp * f, yp * f

    def project(self, position):
        xp = position.x * self.scale
        yp = position.y * self.scale
        zp = position.z * self.scale
        xp, yp = self._remap_radial(xp, yp)

        if self.mode == self.BIRD:
            return xp + self.width / 2, yp + self.height / 2

        return self._tilt(xp, yp, zp)

    def project_grid(self, xp, yp, zp):
        xp, yp = self._remap_radial(xp, yp)

        if self.mode == self.BIRD:
            return xp + self.width / 2, yp + self.height / 2

        return self._tilt(xp, yp, zp)

    def _tilt(self, xp, yp, zp):
        cos_p, sin_p = math.cos(self.pitch), math.sin(self.pitch)
        y2 = -yp * cos_p - zp * sin_p
        z2 = yp * sin_p + zp * cos_p
        w = self.cam_dist / (self.cam_dist + z2)
        return xp * w + self.width / 2, y2 * w + self.height / 2
