"""ui_overlay.py - on-screen info: HUD, per-body labels, the selection
ring, and the inspector panel, plus click-to-select hit-testing. """
import math

import pygame

from body import Star
from constants import G, AU

HUD_TEXT = (225, 227, 232)
HUD_PANEL = (9, 11, 18, 165)
LABEL_COLOR = (176, 182, 196)
SELECTION_COLOR = (235, 240, 255)


class UIOverlay:
    LABEL_BODY_LIMIT = 12  # past this many bodies, skip labels

    def __init__(self, visualizer):
        self.viz = visualizer

    def distance_from_primary(self, body):
        viz = self.viz
        primary = viz._primary_light()
        if primary is None or primary is body:
            return body.position.magnitude()
        return (body.position - primary.position).magnitude()

    def relative_speed(self, body):
        viz = self.viz
        primary = viz._primary_light()
        if primary is None or primary is body:
            return body.velocity.magnitude()
        return (body.velocity - primary.velocity).magnitude()

    def body_stats(self, body):
        stats = [("Mass", f"{body.mass:.3e} kg"),
                 ("Radius", f"{body.radius / 1000:,.0f} km")]
        if isinstance(body, Star):
            stats.append(("Role", "Central body / light source"))
            return stats

        r = self.distance_from_primary(body)
        stats.append(("Distance", f"{r / AU:.3f} AU"))
        speed = self.relative_speed(body)
        stats.append(("Speed", f"{speed / 1000:.2f} km/s"))

        primary = self.viz._primary_light()
        if primary is not None and primary is not body and r > 0:
            period_s = 2 * math.pi * math.sqrt(r ** 3 / (G * primary.mass))
            period_days = period_s / 86400
            period_text = (f"{period_days / 365.25:.2f} yr" if period_days > 500
                            else f"{period_days:.1f} days")
            stats.append(("Period (approx.)", period_text))

        kinetic_energy = 0.5 * body.mass * speed ** 2
        stats.append(("Kinetic energy", f"{kinetic_energy:.3e} J"))
        return stats

    def draw_hud(self):
        viz = self.viz
        lines = [
            "SPACE pause   B bird's-eye   T tilt   F fullscreen   V spiral/static",
            "A add planet   C collision demo   click inspect   right-click remove",
            "Arrow keys camera   +/- zoom   R reset view   ESC menu",
            f"view {viz.camera.mode}  \u00b7  {viz.motion_mode}  \u00b7  bodies {len(viz.sim.bodies)}" +
            ("  \u00b7  PAUSED" if viz.paused else ""),
        ]
        if viz.status_text:
            lines.append(viz.status_text)

        pad_x, pad_y, line_h = 12, 8, 17
        panel_w = max(viz.font.size(line)[0] for line in lines) + pad_x * 2
        panel_h = pad_y * 2 + line_h * len(lines)
        panel = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        pygame.draw.rect(panel, HUD_PANEL, panel.get_rect(), border_radius=7)
        viz.screen.blit(panel, (10, 10))

        for i, line in enumerate(lines):
            surf = viz.font.render(line, True, HUD_TEXT)
            viz.screen.blit(surf, (10 + pad_x, 10 + pad_y + i * line_h))

    def draw_labels(self):
        viz = self.viz
        if len(viz.sim.bodies) > self.LABEL_BODY_LIMIT:
            return
        for body in viz.sim.bodies:
            x, y = viz.camera.project(body.position)
            radius_px = viz._marker_radius(body)
            label = body.name
            if not isinstance(body, Star):
                label += f"  {self.distance_from_primary(body) / AU:.2f} AU"
            surf = viz.label_font.render(label, True, LABEL_COLOR)
            surf.set_alpha(200)
            viz.screen.blit(surf, (x + radius_px + 5, y - 7))

    def draw_selection(self):
        viz = self.viz
        if viz.selected_body is None or viz.selected_body not in viz.sim.bodies:
            viz.selected_body = None
            return
        x, y = viz.camera.project(viz.selected_body.position)
        radius_px = viz._marker_radius(viz.selected_body)
        pulse = 0.5 + 0.5 * math.sin(viz.frame_count * 0.12)
        ring_r = radius_px + 6 + pulse * 3
        pygame.draw.circle(viz.screen, SELECTION_COLOR, (int(x), int(y)), int(ring_r), width=1)

    def draw_inspector_panel(self):
        viz = self.viz
        body = viz.selected_body
        if body is None or body not in viz.sim.bodies:
            return

        panel_w, image_h = 250, 130
        stats = self.body_stats(body)
        header_h = 62
        stats_h = 14 + len(stats) * 20
        panel_h = header_h + image_h + stats_h
        x, y = viz.width - panel_w - 15, 15

        panel = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        pygame.draw.rect(panel, HUD_PANEL, panel.get_rect(), border_radius=10)
        pygame.draw.rect(panel, SELECTION_COLOR, panel.get_rect(), width=1, border_radius=10)

        name_surf = viz.panel_name_font.render(body.name, True, (235, 238, 246))
        panel.blit(name_surf, name_surf.get_rect(midtop=(panel_w / 2, 14)))
        type_label = "Star" if isinstance(body, Star) else "Planet"
        type_surf = viz.label_font.render(type_label, True, LABEL_COLOR)
        panel.blit(type_surf, type_surf.get_rect(midtop=(panel_w / 2, 40)))

        portrait_radius = 55
        color = viz._rgb(body.color)
        if isinstance(body, Star):
            sprite = viz.sphere_cache.star(portrait_radius, color)
        else:
            sprite = viz.sphere_cache.planet(portrait_radius, color, math.radians(-45))
        rect = sprite.get_rect(center=(panel_w // 2, header_h + image_h // 2))
        panel.blit(sprite, rect)

        yy = header_h + image_h + 6
        for label, value in stats:
            text = f"{label}: {value}"
            font = viz.panel_stat_fonts[13]
            for size in (13, 12, 11, 10):
                font = viz.panel_stat_fonts[size]
                if font.size(text)[0] <= panel_w - 32 or size == 10:
                    break
            surf = font.render(text, True, HUD_TEXT)
            panel.blit(surf, (16, yy))
            yy += 20

        viz.screen.blit(panel, (x, y))

    def nearest_body(self, mouse_pos, max_pixels=18):
        viz = self.viz
        nearest, nearest_dist = None, max_pixels
        for body in viz.sim.bodies:
            bx, by = viz.camera.project(body.position)
            dist = math.hypot(bx - mouse_pos[0], by - mouse_pos[1])
            if dist < nearest_dist:
                nearest, nearest_dist = body, dist
        return nearest

    def on_click(self, mouse_pos, button):
        viz = self.viz
        clicked = self.nearest_body(mouse_pos)
        if clicked is None:
            return

        if button == 3:  # right-click: remove
            if clicked is viz.selected_body:
                viz.selected_body = None
            viz.sim.remove_body(clicked)
            viz.status_text = f"Removed {clicked.name}"
            return

        if button == 1:  # left-click: inspect
            viz.selected_body = clicked
            speed = self.relative_speed(clicked)
            viz.status_text = (f"{clicked.name}: mass={clicked.mass:.3e} kg  "
                                f"speed={speed:.0f} m/s  r={self.distance_from_primary(clicked)/AU:.3f} AU")
