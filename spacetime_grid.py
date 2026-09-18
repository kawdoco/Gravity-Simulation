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
        # Batches BATCH points per aalines() call instead of one
        # aaline() call per cell edge - far fewer draw calls at this count.
        BATCH = 6

        def draw_polyline_run(points_x, points_y, colors):
            i = 0
            m = len(points_x)
            while i < m - 1:
                j = min(i + BATCH, m - 1)
                pts = list(zip(points_x[i:j + 1], points_y[i:j + 1]))
                if len(pts) >= 2:
                    pygame.draw.aalines(surface, colors[i], False, pts)
                i = j

        for row in range(n):
            row_x, row_y, row_c, on_screen = [], [], [], False
            for col in range(n):
                x, y = float(sx[row, col]), float(sy[row, col])
                if -50 <= x <= w + 50 and -50 <= y <= h + 50:
                    on_screen = True
                b = float(brightness[row, col])
                row_x.append(x)
                row_y.append(y)
                row_c.append((int(14 + b * 62), int(17 + b * 68), int(26 + b * 78)))
            if on_screen:
                draw_polyline_run(row_x, row_y, row_c)

        for col in range(n):
            col_x, col_y, col_c, on_screen = [], [], [], False
            for row in range(n):
                x, y = float(sx[row, col]), float(sy[row, col])
                if -50 <= x <= w + 50 and -50 <= y <= h + 50:
                    on_screen = True
                b = float(brightness[row, col])
                col_x.append(x)
                col_y.append(y)
                col_c.append((int(14 + b * 62), int(17 + b * 68), int(26 + b * 78)))
            if on_screen:
                draw_polyline_run(col_x, col_y, col_c)
