"""visualizer.py - pygame renderer: game loop that steps physics and
draws the scene each frame. See set_motion_mode() for static/spiral
view modes, and _handle_events()/interaction.handle_held_keys() for
controls.

Core render loop, display/motion-mode management, and bloom only -
three related concerns are composed in from their own files instead:
body_effects.BodyEffects (trails/bodies/bursts), ui_overlay.UIOverlay
(HUD/labels/inspector panel), interaction.InteractionController
(hotkeys/held-key camera control). All three reach back into this
class via self.viz."""
import math

import numpy as np
import pygame

from vector import Vector3D
from camera import Camera
from spacetime_grid import SpacetimeGrid
from starfield import Starfield
from sphere_render import SphereCache
from body import Star
from constants import AU

from .body_effects import BodyEffects
from .interaction import InteractionController
from .ui_overlay import UIOverlay


class Visualizer:
    AUTO_SPIN_DEG_PER_FRAME = 0.05
    SPIRAL_PITCH_DEG = 28
    SPIRAL_DRIFT_MS = (4000, 2000, 20000)  # m/s at the 3 AU reference scale
    SPIRAL_INTRO_FRAMES = 110
    SPIRAL_INTRO_START_ZOOM = 2.3
    SPIRAL_INTRO_START_PITCH_DEG = 62

    @classmethod
    def spiral_drift_vector(cls, view_radius_au):
        scale = view_radius_au / 3.0
        return Vector3D(*(v * scale for v in cls.SPIRAL_DRIFT_MS))

    def __init__(self, simulation, steps_per_frame=4, dt=6 * 3600,
                 view_radius_au=3.0, width=900, height=700, fullscreen=False,
                 motion_mode="static", drift_already_applied=False):
        pygame.init()
        pygame.display.set_caption("Gravity Simulation")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("consolas", 14)
        self.label_font = pygame.font.SysFont("consolas", 11)
        self.panel_name_font = pygame.font.SysFont("consolas", 20, bold=True)
        self.panel_stat_fonts = {size: pygame.font.SysFont("consolas", size)
                                  for size in (13, 12, 11, 10)}

        self.sim = simulation
        self.steps_per_frame = steps_per_frame
        self.dt = dt
        self.view_radius_au = view_radius_au
        self.windowed_size = (width, height)
        self.fullscreen = fullscreen
        self.sphere_cache = SphereCache()

        self._apply_display_mode()

        self.paused = False
        self.running = True
        self.quit_requested = False  # True only if the window was actually closed
        self.status_text = ""
        self.frame_count = 0
        self.selected_body = None

        self.motion_mode = "static"
        self._drift_applied = drift_already_applied
        self._spiral_transition_frame = 0

        self.effects = BodyEffects(self)
        self.interaction = InteractionController(self)
        self.ui = UIOverlay(self)

        if motion_mode == "spiral":
            self.set_motion_mode("spiral")

    def _apply_camera_defaults_for_mode(self):
        if self.motion_mode == "spiral":
            self.camera.mode = Camera.TILT
            self.camera._default_pitch_degrees = self.SPIRAL_PITCH_DEG
            self.camera.pitch = math.radians(self.SPIRAL_PITCH_DEG)
        else:
            self.camera._default_pitch_degrees = self._static_default_pitch_deg

    def set_motion_mode(self, mode):
        self.motion_mode = mode
        if mode == "spiral":
            if not self._drift_applied:
                drift = self.spiral_drift_vector(self.view_radius_au)
                self.sim.apply_drift(drift)
                self._drift_applied = True
            self._apply_camera_defaults_for_mode()
            self.camera.zoom = self.SPIRAL_INTRO_START_ZOOM
            self.camera.pitch = math.radians(self.SPIRAL_INTRO_START_PITCH_DEG)
            self._spiral_transition_frame = 0
            self.status_text = "Spiral mode - the whole system now drifts through space"
        else:
            self._apply_camera_defaults_for_mode()
            self.camera.pitch = math.radians(self._static_default_pitch_deg)
            if self._drift_applied:
                drift = self.spiral_drift_vector(self.view_radius_au)
                self.sim.apply_drift(Vector3D(-drift.x, -drift.y, -drift.z))
                self._drift_applied = False
            self.status_text = "Static mode"

    def _update_camera_follow(self):
        """Eases the camera toward the star each frame in spiral mode."""
        if self.motion_mode != "spiral":
            return
        anchor = max(self.sim.bodies, key=lambda b: b.mass, default=None)
        if anchor is None:
            return
        self._spiral_transition_frame += 1
        self.grid.recenter(self.camera.focus_x, self.camera.focus_y)

        if self._spiral_transition_frame <= self.SPIRAL_INTRO_FRAMES:
            t = self._spiral_transition_frame / self.SPIRAL_INTRO_FRAMES
            eased = 1 - (1 - t) ** 3
            self.camera.zoom = (self.SPIRAL_INTRO_START_ZOOM +
                                 (1.0 - self.SPIRAL_INTRO_START_ZOOM) * eased)
            self.camera.pitch = math.radians(
                self.SPIRAL_INTRO_START_PITCH_DEG +
                (self.SPIRAL_PITCH_DEG - self.SPIRAL_INTRO_START_PITCH_DEG) * eased)
            return
        ease = 0.02
        self.camera.focus_x += (anchor.position.x - self.camera.focus_x) * ease
        self.camera.focus_y += (anchor.position.y - self.camera.focus_y) * ease
        self.camera.focus_z += (anchor.position.z - self.camera.focus_z) * ease

    def _apply_display_mode(self):
        if self.fullscreen:
            self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        else:
            pygame.display.quit()
            pygame.display.init()
            self.screen = pygame.display.set_mode(self.windowed_size)
        self.width, self.height = self.screen.get_size()

        scale = min(self.width, self.height) * 0.42 / (self.view_radius_au * AU)
        self.camera = Camera(self.width, self.height, scale)
        self._static_default_pitch_deg = self.camera._default_pitch_degrees
        if getattr(self, "motion_mode", "static") == "spiral":
            self._apply_camera_defaults_for_mode()
            anchor = max(self.sim.bodies, key=lambda b: b.mass, default=None)
            if anchor is not None:
                self.camera.set_focus(anchor.position.x, anchor.position.y, anchor.position.z)
        self.grid = SpacetimeGrid(extent_au=self.view_radius_au * 1.3)
        self.starfield = Starfield(self.width, self.height)
        self.vignette = self._build_vignette(self.width, self.height)
        self.glow_layer = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        self.trail_layer = pygame.Surface((self.width, self.height), pygame.SRCALPHA)

    def _toggle_fullscreen(self):
        self.fullscreen = not self.fullscreen
        self._apply_display_mode()
        self.status_text = "Fullscreen" if self.fullscreen else "Windowed"

    # ---- shared helpers (used by body_effects.py / ui_overlay.py too) ----
    @staticmethod  # Static Method
    def _rgb(color_name):
        c = pygame.Color(color_name)
        return c.r, c.g, c.b

    def _primary_light(self):
        stars = [b for b in self.sim.bodies if isinstance(b, Star)]
        pool = stars if stars else self.sim.bodies
        return max(pool, key=lambda b: b.mass, default=None)

    @staticmethod  # Static Method
    def _marker_radius(body):
        return max(3, int(math.sqrt(body.marker_size())))  # Polymorphism

    @staticmethod  # Static Method
    def _build_vignette(width, height):
        xs, ys = np.arange(width), np.arange(height)
        xx, yy = np.meshgrid(xs, ys, indexing="ij")
        cx, cy = width / 2, height / 2
        max_dist = math.hypot(cx, cy)
        dist = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2) / max_dist
        strength = np.clip((dist - 0.45) / 0.55, 0.0, 1.0) ** 1.6
        alpha = (strength * 120).astype(np.uint8)

        surf = pygame.Surface((width, height), pygame.SRCALPHA)
        alpha_view = pygame.surfarray.pixels_alpha(surf)
        alpha_view[:, :] = alpha
        del alpha_view
        return surf

    def _blur_down(self, surface, target_w, target_h):
        w, h = surface.get_size()
        current = surface
        while w > target_w * 2 and h > target_h * 2:
            w, h = max(target_w, w // 2), max(target_h, h // 2)
            current = pygame.transform.smoothscale(current, (w, h))
        return pygame.transform.smoothscale(current, (target_w, target_h))

    def _apply_bloom(self):
        w, h = self.width, self.height
        base_w, base_h = max(1, w // 4), max(1, h // 4)
        base = self._blur_down(self.glow_layer, base_w, base_h)

        for divisor, strength in ((7, 0.45), (18, 0.4)):
            target_w, target_h = max(1, w // divisor), max(1, h // divisor)
            small = self._blur_down(base, target_w, target_h)
            blurred = pygame.transform.smoothscale(small, (w, h))
            blurred.set_alpha(int(255 * strength))
            self.screen.blit(blurred, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)

    # ---- frame assembly -------------------------------------------------
    def _render_frame(self):
        self._update_camera_follow()
        self.camera.adjust_yaw(self.AUTO_SPIN_DEG_PER_FRAME)

        PARALLAX_FACTOR = 0.12
        star_offset_x = -self.camera.focus_x * self.camera.scale * self.camera.zoom * PARALLAX_FACTOR
        star_offset_y = -self.camera.focus_y * self.camera.scale * self.camera.zoom * PARALLAX_FACTOR
        self.starfield.draw(self.screen, star_offset_x, star_offset_y)
        self.starfield.draw_twinkle(self.screen, self.frame_count, star_offset_x, star_offset_y)
        self.grid.draw(self.screen, self.sim.bodies, self.camera)

        self.trail_layer.fill((0, 0, 0, 0))
        for body in self.sim.bodies:
            if not isinstance(body, Star):
                self.effects.draw_trail(body)
        self.screen.blit(self.trail_layer, (0, 0))

        self.glow_layer.fill((0, 0, 0, 0))
        light_source = self._primary_light()
        for body in self.sim.bodies:
            self.effects.draw_body(body, light_source)
        self.effects.draw_bursts()
        self._apply_bloom()

        self.ui.draw_labels()
        self.ui.draw_selection()
        self.ui.draw_inspector_panel()
        self.screen.blit(self.vignette, (0, 0))
        self.ui.draw_hud()

        self.frame_count += 1

    # ---- events -------------------------------------------------------
    def _handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                self.quit_requested = True
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False  # Esc means back to the menu, not quit
                elif event.key == pygame.K_SPACE:
                    self.paused = not self.paused
                elif event.key == pygame.K_b:
                    self.camera.mode = Camera.BIRD
                elif event.key == pygame.K_t:
                    self.camera.mode = Camera.TILT
                elif event.key == pygame.K_f:
                    self._toggle_fullscreen()
                elif event.key == pygame.K_a:
                    self.interaction.add_random_body()
                elif event.key == pygame.K_c:
                    self.interaction.spawn_collision_demo()
                elif event.key == pygame.K_r:
                    self.interaction.reset_view()
                elif event.key == pygame.K_v:
                    self.set_motion_mode("spiral" if self.motion_mode == "static" else "static")
            elif event.type == pygame.MOUSEBUTTONDOWN:
                self.ui.on_click(event.pos, event.button)
            elif event.type == pygame.MOUSEWHEEL:
                self.camera.adjust_zoom(1.1 ** event.y)

    # ---- main loop ---------------------------------------------------
    def _step_physics(self):
        before = {body.name: body.position.as_tuple() for body in self.sim.bodies}
        for _ in range(self.steps_per_frame):
            self.sim.step(self.dt)
        after_names = {body.name for body in self.sim.bodies}

        for name, pos in before.items():
            if name not in after_names:
                self.effects.bursts.append({"pos": Vector3D(*pos), "age": 0})
                if self.selected_body is not None and self.selected_body.name == name:
                    self.selected_body = None

    def run(self):
        while self.running:
            self._handle_events()
            self.interaction.handle_held_keys()
            if not self.paused:
                self._step_physics()
            self._render_frame()
            pygame.display.flip()
            self.clock.tick(60)
        pygame.quit()
