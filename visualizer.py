"""
visualizer.py

Pygame-based renderer: a real game loop


Controls:
  - Left-click a body   -> inspect it (name/mass/speed shown in the HUD)
  - Right-click a body  -> remove it
  - 'a'                 -> add a new planet at a random position, 
  - 'b' / 't'            -> bird's-eye view / tilted spacetime-fabric view
  - Spacebar             -> pause / resume
  - Esc                  -> quit
"""
import math
import random

import pygame

from vector import Vector3D
from body import Planet, Star, CelestialBody
from camera import Camera
from spacetime_grid import SpacetimeGrid
from starfield import Starfield
from sphere_render import SphereCache
from constants import G, AU

HUD_TEXT = (225, 227, 232)
HUD_PANEL = (9, 11, 18, 165)


class Visualizer:
    def __init__(self, simulation, steps_per_frame=4, dt=6 * 3600,
                 view_radius_au=3.0, width=900, height=700):
        pygame.init()
        pygame.display.set_caption("Gravity Simulation")
        self.screen = pygame.display.set_mode((width, height))
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("consolas", 14)
        self.sim = simulation
        self.steps_per_frame = steps_per_frame
        self.dt = dt
        self.view_radius_au = view_radius_au
        self.width, self.height = width, height
        scale = min(width, height) * 0.42 / (view_radius_au * AU)
        self.camera = Camera(width, height, scale)
        self.grid = SpacetimeGrid(extent_au=view_radius_au * 1.3)
        self.starfield = Starfield(width, height)
        self.sphere_cache = SphereCache()
        self.glow_layer = pygame.Surface((width, height), pygame.SRCALPHA)
        self.trail_layer = pygame.Surface((width, height), pygame.SRCALPHA)

        self.paused = False
        self.running = True
        self.status_text = ""

    # ---- helpers -------------------------------------------------------
    @staticmethod
    def _rgb(color_name):
        c = pygame.Color(color_name)
        return c.r, c.g, c.b

    def _primary_light(self):
        stars = [b for b in self.sim.bodies if isinstance(b, Star)]
        pool = stars if stars else self.sim.bodies
        return max(pool, key=lambda b: b.mass, default=None)

    @staticmethod
    def _marker_radius(body):
        return max(3, int(math.sqrt(body.marker_size())))

    # ---- drawing: trails -------------------------------------------------
    def _draw_trail(self, body, max_points=45, bands=6):
    
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

        projected = [self.camera.project(Vector3D(*p)) for p in sampled]
        color = self._rgb(body.color)

        band_size = max(1, m // bands)
        for b in range(bands):
            start = b * band_size
            end = min(m, start + band_size + 1)  # +1 so bands connect with no gap
            if end - start < 2:
                continue
            alpha = int(8 + 110 * (b / max(1, bands - 1)))
            pygame.draw.aalines(self.trail_layer, (*color, alpha), False, projected[start:end])

    # ---- drawing: bodies -------------------------------------------------
    def _draw_body(self, body, light_source):
        x, y = self.camera.project(body.position)
        color = self._rgb(body.color)
        radius_px = self._marker_radius(body)

        if isinstance(body, Star):
            sprite = self.sphere_cache.star(radius_px, color)
            glow_radius = radius_px * 2.2
            glow_alpha = 110
            glow = pygame.Surface((glow_radius * 2, glow_radius * 2), pygame.SRCALPHA)
            pygame.draw.circle(glow, (*color, glow_alpha), (glow_radius, glow_radius), glow_radius)
            self.glow_layer.blit(glow, (x - glow_radius, y - glow_radius),
                                  special_flags=pygame.BLEND_RGBA_ADD)
        else:
            light_angle = 0.0
            if light_source is not None and light_source is not body:
                lx, ly = self.camera.project(light_source.position)
                light_angle = math.atan2(ly - y, lx - x)
            sprite = self.sphere_cache.planet(radius_px, color, light_angle)
           

        rect = sprite.get_rect(center=(int(x), int(y)))
        self.screen.blit(sprite, rect)

    def _blur_down(self, surface, target_w, target_h):
        w, h = surface.get_size()
        current = surface
        while w > target_w * 2 and h > target_h * 2:
            w, h = max(target_w, w // 2), max(target_h, h // 2)
            current = pygame.transform.smoothscale(current, (w, h))
        return pygame.transform.smoothscale(current, (target_w, target_h))

    def _apply_bloom(self):
        w, h = self.width, self.height
        for divisor, strength in ((7, 0.45), (18, 0.4)):
            small = self._blur_down(self.glow_layer, max(1, w // divisor), max(1, h // divisor))
            blurred = pygame.transform.smoothscale(small, (w, h))
            blurred.set_alpha(int(255 * strength))
            self.screen.blit(blurred, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)

    # ---- drawing: HUD -------------------------------------------------
    def _draw_hud(self):
        lines = [
            "SPACE pause   B bird's-eye   T tilt   A add planet   click inspect   right-click remove   ESC quit",
            f"view {self.camera.mode}  \u00b7  bodies {len(self.sim.bodies)}" +
            ("  \u00b7  PAUSED" if self.paused else ""),
        ]
        if self.status_text:
            lines.append(self.status_text)

        pad_x, pad_y, line_h = 12, 8, 17
        panel_w = max(self.font.size(line)[0] for line in lines) + pad_x * 2
        panel_h = pad_y * 2 + line_h * len(lines)
        panel = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        pygame.draw.rect(panel, HUD_PANEL, panel.get_rect(), border_radius=7)
        self.screen.blit(panel, (10, 10))

        for i, line in enumerate(lines):
            surf = self.font.render(line, True, HUD_TEXT)
            self.screen.blit(surf, (10 + pad_x, 10 + pad_y + i * line_h))

    # ---- frame assembly -------------------------------------------------
    def _render_frame(self):
        self.starfield.draw(self.screen)
        self.grid.draw(self.screen, self.sim.bodies, self.camera)

        self.trail_layer.fill((0, 0, 0, 0))
        for body in self.sim.bodies:
            self._draw_trail(body)
        self.screen.blit(self.trail_layer, (0, 0))

        self.glow_layer.fill((0, 0, 0, 0))
        light_source = self._primary_light()
        for body in self.sim.bodies:
            self._draw_body(body, light_source)
        self._apply_bloom()

        self._draw_hud()

    # ---- interaction -------------------------------------------------
    def _nearest_body(self, mouse_pos, max_pixels=18):
        nearest, nearest_dist = None, max_pixels
        for body in self.sim.bodies:
            bx, by = self.camera.project(body.position)
            dist = math.hypot(bx - mouse_pos[0], by - mouse_pos[1])
            if dist < nearest_dist:
                nearest, nearest_dist = body, dist
        return nearest

    def _on_click(self, mouse_pos, button):
        clicked = self._nearest_body(mouse_pos)
        if clicked is None:
            return

        if button == 3:  # right-click: remove
            self.sim.remove_body(clicked)
            self.status_text = f"Removed {clicked.name}"
            return

        if button == 1:  # left-click: inspect
            speed = clicked.velocity.magnitude()
            self.status_text = (f"{clicked.name}: mass={clicked.mass:.3e} kg  "
                                 f"speed={speed:.0f} m/s  r={clicked.position.magnitude()/AU:.3f} AU")

    def _add_random_body(self):
        limit = self.view_radius_au * AU
        position = Vector3D(random.uniform(-limit, limit), random.uniform(-limit, limit), 0)

        anchor = max(self.sim.bodies, key=lambda b: b.mass, default=None)
        velocity = Vector3D(0, 0, 0)
        if anchor is not None and anchor.position.distance_to(position) > 0:
            radius_vec = position - anchor.position
            r = radius_vec.magnitude()
            speed = (G * anchor.mass / r) ** 0.5
            tangent = Vector3D(-radius_vec.y, radius_vec.x, 0).normalized()
            velocity = anchor.velocity + tangent * speed

        mass = 5e23
        new_body = Planet(f"P{len(self.sim.bodies)}", mass, CelestialBody.radius_from_mass(mass),
                           position, velocity, color="#9fb8c9")
        self.sim.add_body(new_body)
        self.status_text = f"Added {new_body.name}"

    def _handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                elif event.key == pygame.K_SPACE:
                    self.paused = not self.paused
                elif event.key == pygame.K_b:
                    self.camera.mode = Camera.BIRD
                elif event.key == pygame.K_t:
                    self.camera.mode = Camera.TILT
                elif event.key == pygame.K_a:
                    self._add_random_body()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                self._on_click(event.pos, event.button)

    # ---- main loop ---------------------------------------------------
    def run(self):
        while self.running:
            self._handle_events()
            if not self.paused:
                for _ in range(self.steps_per_frame):
                    self.sim.step(self.dt)
            self._render_frame()
            pygame.display.flip()
            self.clock.tick(60)
        pygame.quit()
