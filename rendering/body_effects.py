"""body_effects.py - per-body visual effects: trails, sphere/corona/ring
drawing, and collision-flash bursts.."""
import colorsys
import math

import pygame

from vector import Vector3D
from body import Star

BURST_COLOR = (255, 225, 170)


class BodyEffects:
    BURST_LIFETIME = 24  # frames a collision flash stays visible

    def __init__(self, visualizer):
        self.viz = visualizer
        self.bursts = []

    def vivid_trail_color(self, body):
        r, g, b = self.viz._rgb(body.color)
        h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
        if s < 0.15:
            h = (hash(body.name) % 360) / 360.0
        r2, g2, b2 = colorsys.hsv_to_rgb(h, 0.88, 1.0)
        return int(r2 * 255), int(g2 * 255), int(b2 * 255)

    def draw_star_spine(self, body, max_points=140, bands=5):
        points = body.trail
        n = len(points)
        if n < 2:
            return
        step = max(1, n // max_points)
        sampled = points[::step]
        if sampled[-1] != points[-1]:
            sampled.append(points[-1])
        m = len(sampled)
        if m < 2:
            return

        projected = [self.viz.camera.project(Vector3D(*p)) for p in sampled]
        color = (255, 210, 130)

        band_size = max(1, m // bands)
        for b in range(bands):
            start = b * band_size
            end = min(m, start + band_size + 1)
            if end - start < 2:
                continue
            t = b / max(1, bands - 1)
            alpha = int(90 + 150 * t)
            width = 4 if t > 0.7 else (3 if t > 0.3 else 2)
            pygame.draw.lines(self.viz.trail_layer, (*color, alpha), False, projected[start:end], width)
            if b >= bands - 2:
                glow_alpha = int(30 + 50 * t)
                pygame.draw.lines(self.viz.glow_layer, (*color, glow_alpha), False, projected[start:end], 7)

    def draw_trail(self, body, star_screens, max_points=90, bands=6):
        points = body.trail
        n = len(points)
        if n < 2:
            return
        step = max(1, n // max_points)
        sampled = points[::step]
        if sampled[-1] != points[-1]:
            sampled.append(points[-1])
        m = len(sampled)
        if m < 2:
            return

        projected = [self.viz.camera.project(Vector3D(*p)) for p in sampled]
        color = self.vivid_trail_color(body)

        band_size = max(1, m // bands)
        for b in range(bands):
            start = b * band_size
            end = min(m, start + band_size + 1)
            if end - start < 2:
                continue
            t = b / max(1, bands - 1)
            alpha = int(45 + 200 * t)
            pygame.draw.aalines(self.viz.trail_layer, (*color, alpha), False, projected[start:end])
            if b == bands - 1 and not self.segment_near_star(projected[start:end], star_screens):
                # skip the glow near a star - it smears into a lopsided
                pygame.draw.lines(self.viz.glow_layer, (*color, 70), False, projected[start:end], 3)

    @staticmethod  # Static Method
    def segment_near_star(points, star_screens, margin=1.4):
        for sx, sy, glow_radius in star_screens:
            threshold2 = (glow_radius * margin) ** 2
            for px, py in points:
                if (px - sx) ** 2 + (py - sy) ** 2 <= threshold2:
                    return True
        return False

    def draw_body(self, body, light_source):
        viz = self.viz
        x, y = viz.camera.project(body.position)
        color = viz._rgb(body.color)
        radius_px = viz._marker_radius(body)  # Polymorphism

        if isinstance(body, Star):
            sprite = viz.sphere_cache.star(radius_px, color)
            # afford more glow
            glow_radius = radius_px * viz.STAR_GLOW_RADIUS_FACTOR
            glow_alpha = 80
            glow = pygame.Surface((glow_radius * 2, glow_radius * 2), pygame.SRCALPHA)
            pygame.draw.circle(glow, (*color, glow_alpha), (glow_radius, glow_radius), glow_radius)
            viz.glow_layer.blit(glow, (x - glow_radius, y - glow_radius),
                                 special_flags=pygame.BLEND_RGBA_ADD)
            self.draw_corona(x, y, radius_px, color)
        else:
            light_angle = 0.0
            if light_source is not None and light_source is not body:
                lx, ly = viz.camera.project(light_source.position)
                light_angle = math.atan2(ly - y, lx - x)
            sprite = viz.sphere_cache.planet(radius_px, color, light_angle)
            if getattr(body, "has_ring", False):
                self.draw_ring(x, y, radius_px, color)

        rect = sprite.get_rect(center=(int(x), int(y)))
        viz.screen.blit(sprite, rect)

    def draw_corona(self, x, y, radius_px, color):
        length = radius_px * 3.6
        for i in range(3):  # 3 lines through center = a 6-point star
            angle = self.viz.frame_count * 0.0025 + i * math.pi / 3
            dx, dy = math.cos(angle), math.sin(angle)
            p1 = (x - dx * length, y - dy * length)
            p2 = (x + dx * length, y + dy * length)
            pygame.draw.line(self.viz.glow_layer, (*color, 26), p1, p2, 2)

    def draw_ring(self, x, y, radius_px, color):
        rw, rh = radius_px * 4.6, radius_px * 1.5
        ring = pygame.Surface((int(rw), int(rh)), pygame.SRCALPHA)
        pygame.draw.ellipse(ring, (*color, 150), ring.get_rect(),
                             width=max(2, int(radius_px * 0.22)))
        tilted = pygame.transform.rotozoom(ring, 14, 1.0)
        rect = tilted.get_rect(center=(int(x), int(y)))
        self.viz.screen.blit(tilted, rect)

    def draw_bursts(self):
        remaining = []
        for burst in self.bursts:
            burst["age"] += 1
            t = burst["age"] / self.BURST_LIFETIME
            if t >= 1.0:
                continue
            x, y = self.viz.camera.project(burst["pos"])
            radius = 5 + t * 42
            alpha = int(210 * (1 - t))
            size = int(radius * 2 + 6)
            ring = pygame.Surface((size, size), pygame.SRCALPHA)
            pygame.draw.circle(ring, (*BURST_COLOR, alpha), (size // 2, size // 2),
                                int(radius), width=3)
            self.viz.glow_layer.blit(ring, (x - size / 2, y - size / 2),
                                      special_flags=pygame.BLEND_RGBA_ADD)
            remaining.append(burst)
        self.bursts = remaining
