"""sphere_render.py - turns a flat body color into a shaded-sphere sprite."""
import math

import numpy as np
import pygame


def render_planet(radius_px, color, light_angle=0.0, ambient=0.16):
    r = max(2, int(round(radius_px)))
    size = r * 2 + 1
    xs, ys = np.arange(size), np.arange(size)
    xx, yy = np.meshgrid(xs, ys)
    dx = (xx - r) / r
    dy = (yy - r) / r
    dist2 = dx * dx + dy * dy
    mask = dist2 <= 1.0

    dz = np.sqrt(np.clip(1.0 - dist2, 0.0, 1.0))

    lx, ly, lz = math.cos(light_angle), math.sin(light_angle), 0.35
    l_len = math.sqrt(lx * lx + ly * ly + lz * lz)
    lx, ly, lz = lx / l_len, ly / l_len, lz / l_len

    n_dot_l = dx * lx + dy * ly + dz * lz
    diffuse = np.clip(n_dot_l, 0.0, 1.0)
    limb = np.clip(dz, 0.0, 1.0) ** 0.35
    brightness = (ambient + (1.0 - ambient) * diffuse) * (0.78 + 0.22 * limb)

    base = np.array(color, dtype=np.float32)
    rgb = np.clip(base[None, None, :] * brightness[:, :, None], 0, 255).astype(np.float32)

    # Specular highlight (Blinn-Phong), lit side only
    hx, hy, hz = lx, ly, lz + 1.0
    h_len = math.sqrt(hx * hx + hy * hy + hz * hz)
    hx, hy, hz = hx / h_len, hy / h_len, hz / h_len
    n_dot_h = np.clip(dx * hx + dy * hy + dz * hz, 0.0, 1.0)
    specular = np.where(n_dot_l > 0, n_dot_h ** 28, 0.0) * 0.5
    rgb += 255.0 * specular[:, :, None]

    rgb = np.clip(rgb, 0, 255).astype(np.uint8)
    alpha = np.where(mask, 255, 0).astype(np.uint8)
    rgba = np.dstack([rgb, alpha])

    return pygame.image.frombuffer(rgba.tobytes(), (size, size), "RGBA").convert_alpha()


def render_star(radius_px, color):
    r = max(2, int(round(radius_px)))
    size = r * 2 + 1
    xs, ys = np.arange(size), np.arange(size)
    xx, yy = np.meshgrid(xs, ys)
    dx = (xx - r) / r
    dy = (yy - r) / r
    dist = np.sqrt(dx * dx + dy * dy)
    mask = dist <= 1.0

    limb = np.clip(1.0 - 0.32 * dist ** 2, 0.0, 1.0)
    core = np.clip(1.0 - dist, 0.0, 1.0) ** 3

    base = np.array(color, dtype=np.float32)
    white = np.array([255.0, 255.0, 255.0])
    rgb = base[None, None, :] * limb[:, :, None]
    rgb = rgb + (white - base)[None, None, :] * core[:, :, None] * 0.38
    rgb = np.clip(rgb, 0, 255).astype(np.uint8)
    alpha = np.where(mask, 255, 0).astype(np.uint8)
    rgba = np.dstack([rgb, alpha])

    return pygame.image.frombuffer(rgba.tobytes(), (size, size), "RGBA").convert_alpha()


class SphereCache:
    def __init__(self):
        self._planets = {}  # Encapsulation
        self._stars = {}  # Encapsulation

    def planet(self, radius_px, color, light_angle):
        key = (max(2, int(round(radius_px))), tuple(color))
        base = self._planets.get(key)
        if base is None:
            base = render_planet(key[0], key[1], light_angle=0.0)
            self._planets[key] = base
        degrees = -math.degrees(light_angle)
        return pygame.transform.rotozoom(base, degrees, 1.0)

    def star(self, radius_px, color):
        key = (max(2, int(round(radius_px))), tuple(color))
        surf = self._stars.get(key)
        if surf is None:
            surf = render_star(key[0], key[1])
            self._stars[key] = surf
        return surf
