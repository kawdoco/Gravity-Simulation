"""
starfield.py

A static, procedurally generated star field

Star brightness follows a power-law skew (many faint stars, a few
bright ones) rather than a flat random distribution - closer to how
real star fields actually look, and closer to the muted, low-key
palette real astrophotography uses rather than a "cartoon space"
scattering of big uniform dots.
"""
import math

import numpy as np
import pygame


class Starfield:
    """Creates a decorative star background"""

    SPACE_COLOR = (3, 4, 9)  # near-black with the faintest blue cast,
                              # closer to a real long-exposure sky than
                              # flat (0, 0, 0)

    def __init__(self, width, height, density=0.00028, seed=7):
        self.surface = self._build(width, height, density, seed)

    @classmethod
    def _build(cls, width, height, density, seed):
        rng = np.random.default_rng(seed)
        surface = pygame.Surface((width, height))
        surface.fill(cls.SPACE_COLOR)
        cls._draw_milky_band(surface, width, height, rng)
        cls._draw_stars(surface, width, height, density, rng)
        return surface

    @staticmethod
    def _draw_milky_band(surface, width, height, rng):
        """create random values for galaxy glow."""
        # randoms values for galaxy glow, random values for RGB format, full screen size  and get noise values from the image
        # without needing a real Perlin/Simplex noise library.
        coarse = (rng.random((10, 6)) * 255).astype(np.uint8)
        coarse_rgb = np.repeat(coarse[:, :, None], 3, axis=2)
        noise_surf = pygame.transform.smoothscale(
            pygame.surfarray.make_surface(coarse_rgb), (width, height))
        noise = pygame.surfarray.array3d(noise_surf)[:, :, 0].astype(np.float32) / 255.0
        noise = 0.3 + 0.7 * noise  # keep a floor so it never fully vanishes

        xx, yy = np.meshgrid(np.arange(width), np.arange(height), indexing="ij")
        cx, cy = width * 0.5, height * 0.6
        angle = math.radians(25)
        dx, dy = xx - cx, yy - cy
        ry = -dx * math.sin(angle) + dy * math.cos(angle)  # distance across the band
        band_half_width = height * 0.22
        gauss = np.exp(-(ry ** 2) / (2 * band_half_width ** 2))

        peak = 24.0  # small max brightness added - subtle by design
        tint = np.array([46, 54, 80], dtype=np.float32) / 255.0  # cool blue-grey
        add = (gauss * noise)[:, :, None] * tint[None, None, :] * peak

        pixels = pygame.surfarray.pixels3d(surface)
        pixels[:] = np.clip(pixels.astype(np.float32) + add, 0, 255).astype(np.uint8)
        del pixels

    @staticmethod
    def _draw_stars(surface, width, height, density, rng): # calculate how many stars to create
        n = max(1, int(width * height * density))
        xs = rng.integers(0, width, n)
        ys = rng.integers(0, height, n)
        # Power-law brightness: mostly dim background stars, a few
        # standouts - not a uniform scatter of equally-bright dots.
        brightness = np.clip(rng.power(3.2, n) * 245 + 12, 0, 255).astype(int)
        tint = rng.random(n)

        # random values for star colors

        pixels = pygame.surfarray.pixels3d(surface)
        for x, y, b, t in zip(xs, ys, brightness, tint):
            b = int(b)
            if t < 0.08:        # cool blue-white star
                pixels[x, y] = (int(b * 0.78), int(b * 0.88), b)
            elif t > 0.94:      # warm star
                pixels[x, y] = (b, int(b * 0.86), int(b * 0.68))
            else:               # ordinary white star
                pixels[x, y] = (b, b, b)
        del pixels

        # Helps to add small sparkle to the brightest stars , set sparkle length,sparkle color and horizontal sparkles and vertical sparkles.
        bright_idx = np.argsort(brightness)[-max(1, int(n * 0.008)):]
        for i in bright_idx:
            x, y, b = int(xs[i]), int(ys[i]), int(brightness[i])
            length = int(rng.integers(3, 7))
            c = (min(255, b + 20),) * 3
            pygame.draw.line(surface, c, (x - length, y), (x + length, y))
            pygame.draw.line(surface, c, (x, y - length), (x, y + length))

    def draw(self, target):
        target.blit(self.surface, (0, 0))
