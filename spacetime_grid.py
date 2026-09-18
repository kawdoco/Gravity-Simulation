"""spacetime_grid.py - the "dented fabric" grid under the bodies.

    height = peak / sqrt(1 + distance^2 / width^2)
"""
import math
import numpy as np
import pygame

from constants import AU


class SpacetimeGrid:
    def __init__(self, extent_au=4.0, step_au=0.15):
        self.extent_au = extent_au
        self.step_au = step_au
        self.n = int(2 * extent_au / step_au) + 1
        self._build_mesh(0.0, 0.0)

    def _build_mesh(self, center_x, center_y):  # Encapsulation
        coords_x = np.linspace(center_x - self.extent_au * AU, center_x + self.extent_au * AU, self.n)
        coords_y = np.linspace(center_y - self.extent_au * AU, center_y + self.extent_au * AU, self.n)
        self.gx, self.gy = np.meshgrid(coords_x, coords_y)

    def recenter(self, center_x, center_y):
        """Keeps the grid under the star as it drifts in spiral mode."""
        self._build_mesh(center_x, center_y)

    @staticmethod  # Static Method
    def _peak_height(mass):
        peak = 25.0 * math.log10(mass) - 560.0
        return max(10.0, min(peak, 220.0))

    @staticmethod  # Static Method
    def _well_width(mass):
        width_au = 0.14 * (mass / 5.972e24) ** (1 / 3)
        return max(0.05, min(width_au, 0.9)) * AU

    def _heights(self, bodies):  # Encapsulation
        z = np.zeros((self.n, self.n))
        for body in bodies:
            peak = self._peak_height(body.mass)
            width = self._well_width(body.mass)
            dx = self.gx - body.position.x
            dy = self.gy - body.position.y
            z += peak / np.sqrt(1.0 + (dx * dx + dy * dy) / (width * width))
        return z

    def draw(self, surface, bodies, camera):
        if not bodies:
            return
        z = self._heights(bodies)
        peak = max(float(z.max()), 1.0)
        brightness = np.clip((z / peak) ** 0.45, 0.0, 1.0)

        sx, sy = camera.project_grid(self.gx * camera.scale, self.gy * camera.scale, -z)

        n = self.n
        w, h = surface.get_width(), surface.get_height()
        for row in range(n - 1):
            for col in range(n - 1):
                x0, y0 = sx[row, col], sy[row, col]
                if not (-50 <= x0 <= w + 50 and -50 <= y0 <= h + 50):
                    continue
                b = float(brightness[row, col])
                color = (int(14 + b * 62), int(17 + b * 68), int(26 + b * 78))
                x1, y1 = sx[row, col + 1], sy[row, col + 1]
                x2, y2 = sx[row + 1, col], sy[row + 1, col]
                pygame.draw.aaline(surface, color, (x0, y0), (x1, y1))
                pygame.draw.aaline(surface, color, (x0, y0), (x2, y2))
