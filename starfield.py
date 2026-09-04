"""starfield.py - procedural star field, split into two layers:
a fixed base (space color + Milky Way band) and a tileable star
layer that pans as the camera's focus moves, so "spiral" mode reads
as the camera actually traveling somewhere."""
import math

import numpy as np
import pygame


class Starfield: #multi layer background
    SPACE_COLOR = (3, 4, 9)

    def __init__(self, width, height, density=0.00028, seed=7):
        self.width = width #display width
        self.height = height #display height
        rng = np.random.default_rng(seed)

        base = pygame.Surface((width, height))
        base.fill(self.SPACE_COLOR)
        self._draw_milky_band(base, width, height, rng)
        self.base = base

        xs, ys, brightness, tint = self._star_positions(width, height, density, rng)
        self.stars = pygame.Surface((width, height), pygame.SRCALPHA)
        self._draw_stars(self.stars, xs, ys, brightness, tint)
        self.twinkle_stars = self._pick_twinkle_stars(xs, ys, brightness, tint, rng)

    @staticmethod  # Static Method
    def _pick_twinkle_stars(xs, ys, brightness, tint, rng, count=20):
        candidates = np.where(brightness > np.percentile(brightness, 80))[0]
        if len(candidates) == 0:
            return []
        chosen = rng.choice(candidates, size=min(count, len(candidates)), replace=False)
        stars = []
        for i in chosen:
            b = int(brightness[i])
            if tint[i] < 0.08:
                color = (int(b * 0.78), int(b * 0.88), b)
            elif tint[i] > 0.94:
                color = (b, int(b * 0.86), int(b * 0.68))
            else:
                color = (b, b, b)
            stars.append({
                "x": int(xs[i]), "y": int(ys[i]), "color": color,
                "phase": rng.uniform(0, 2 * math.pi), "speed": rng.uniform(0.02, 0.055),
            })
        return stars

    def _wrapped_positions(self, x, y, offset_x, offset_y):  # Encapsulation
        bx = (x + offset_x) % self.width
        by = (y + offset_y) % self.height
        for sx in (bx, bx - self.width):
            for sy in (by, by - self.height):
                if 0 <= sx < self.width and 0 <= sy < self.height:
                    yield sx, sy

    def draw_twinkle(self, target, frame_count, offset_x=0, offset_y=0):
        for star in self.twinkle_stars:
            pulse = 0.5 + 0.5 * math.sin(frame_count * star["speed"] + star["phase"])
            scale = 0.55 + 0.45 * pulse
            color = tuple(min(255, int(c * scale) + 10) for c in star["color"])
            radius = 1 if pulse < 0.6 else 2
            for sx, sy in self._wrapped_positions(star["x"], star["y"], offset_x, offset_y):
                pygame.draw.circle(target, color, (int(sx), int(sy)), radius)

    @staticmethod  # Static Method
    def _draw_milky_band(surface, width, height, rng):
        coarse = (rng.random((10, 6)) * 255).astype(np.uint8)
        coarse_rgb = np.repeat(coarse[:, :, None], 3, axis=2)
        noise_surf = pygame.transform.smoothscale(
            pygame.surfarray.make_surface(coarse_rgb), (width, height))
        noise = pygame.surfarray.array3d(noise_surf)[:, :, 0].astype(np.float32) / 255.0
        noise = 0.3 + 0.7 * noise

        xx, yy = np.meshgrid(np.arange(width), np.arange(height), indexing="ij")
        cx, cy = width * 0.5, height * 0.6
        angle = math.radians(25)
        dx, dy = xx - cx, yy - cy
        ry = -dx * math.sin(angle) + dy * math.cos(angle)
        band_half_width = height * 0.22
        gauss = np.exp(-(ry ** 2) / (2 * band_half_width ** 2))

        peak = 24.0
        tint = np.array([46, 54, 80], dtype=np.float32) / 255.0
        add = (gauss * noise)[:, :, None] * tint[None, None, :] * peak

        pixels = pygame.surfarray.pixels3d(surface)
        pixels[:] = np.clip(pixels.astype(np.float32) + add, 0, 255).astype(np.uint8)
        del pixels

    @staticmethod  # Static Method
    def _star_positions(width, height, density, rng):  # Encapsulation
        n = max(1, int(width * height * density))
        xs = rng.integers(0, width, n)
        ys = rng.integers(0, height, n)
        brightness = np.clip(rng.power(3.2, n) * 245 + 12, 0, 255).astype(int)
        tint = rng.random(n)
        return xs, ys, brightness, tint

    @staticmethod  # Static Method
    def _draw_stars(surface, xs, ys, brightness, tint):
        pixels = pygame.surfarray.pixels3d(surface)
        alpha = pygame.surfarray.pixels_alpha(surface)
        for x, y, b, t in zip(xs, ys, brightness, tint):
            b = int(b)
            if t < 0.08:
                pixels[x, y] = (int(b * 0.78), int(b * 0.88), b)
            elif t > 0.94:
                pixels[x, y] = (b, int(b * 0.86), int(b * 0.68))
            else:
                pixels[x, y] = (b, b, b)
            alpha[x, y] = 255
        del pixels
        del alpha

    def draw(self, target, offset_x=0, offset_y=0):
        target.blit(self.base, (0, 0))
        if offset_x == 0 and offset_y == 0:
            target.blit(self.stars, (0, 0))
            return
        w, h = self.width, self.height
        ox = int(offset_x) % w
        oy = int(offset_y) % h
        for dx in (ox - w, ox):
            for dy in (oy - h, oy):
                target.blit(self.stars, (dx, dy))
