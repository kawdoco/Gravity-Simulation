
import math


class Camera:
    BIRD = "bird"
    TILT = "tilt"

    def __init__(self, width, height, scale, pitch_degrees=50, cam_dist=2600):
        self.width = width
        self.height = height
        self.scale = scale          # pixels per meter
        self.pitch = math.radians(pitch_degrees)
        self.cam_dist = cam_dist    # larger -> less perspective distortion
        self.mode = self.TILT

    def toggle(self):
        self.mode = self.BIRD if self.mode == self.TILT else self.TILT

    def project(self, position):
    
        xp = position.x * self.scale
        yp = position.y * self.scale
        zp = position.z * self.scale

        if self.mode == self.BIRD:
            return xp + self.width / 2, yp + self.height / 2

        return self._tilt(xp, yp, zp)

    def project_grid(self, xp, yp, zp):
        
        if self.mode == self.BIRD:
            return xp + self.width / 2, yp + self.height / 2

        return self._tilt(xp, yp, zp)

    def _tilt(self, xp, yp, zp):
        
        cos_p, sin_p = math.cos(self.pitch), math.sin(self.pitch)
        y2 = yp * cos_p - zp * sin_p
        z2 = yp * sin_p + zp * cos_p
        w = self.cam_dist / (self.cam_dist + z2)
        return xp * w + self.width / 2, y2 * w + self.height / 2
