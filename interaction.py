"""interaction.py - player-triggered actions: spawning a random planet
or a guaranteed collision pair, resetting the camera view, and
held-key camera control. Split out of visualizer.py; pairs naturally
with body.py since two of these create new CelestialBody instances.
Reaches back into the parent Visualizer via self.viz for the
simulation/camera/timing state it needs."""
import random

import pygame

from vector import Vector3D
from body import Planet, CelestialBody
from constants import G, AU


class InteractionController:
    def __init__(self, visualizer):
        self.viz = visualizer

    def spawn_collision_demo(self):
        viz = self.viz
        anchor = max(viz.sim.bodies, key=lambda b: b.mass, default=None)
        origin = anchor.position if anchor else Vector3D(0, 0, 0)
        gap = viz.view_radius_au * AU * 0.3
        y_offset = viz.view_radius_au * AU * 0.45

        steps_to_impact = 90
        closing_speed = gap / (steps_to_impact * viz.dt)

        mass = 5e23
        natural_radius = CelestialBody.radius_from_mass(mass)
        safe_radius = 1.5 * gap / steps_to_impact  # big enough a timestep can't skip past it
        radius = max(natural_radius, safe_radius)

        n = len(viz.sim.bodies)
        p1 = Vector3D(origin.x - gap, origin.y + y_offset, origin.z)
        p2 = Vector3D(origin.x + gap, origin.y + y_offset, origin.z)
        drift = Vector3D(0, 0, 0)
        if viz._drift_applied:
            drift = viz.spiral_drift_vector(viz.view_radius_au)
        viz.sim.add_body(Planet(f"Demo{n}A", mass, radius, p1, Vector3D(closing_speed, 0, 0) + drift,
                                 color="#ffb37a"))
        viz.sim.add_body(Planet(f"Demo{n + 1}B", mass, radius, p2, Vector3D(-closing_speed, 0, 0) + drift,
                                 color="#7ad1ff"))
        outcome = "merge" if viz.sim.restitution <= 0 else "bounce"
        viz.status_text = f"Collision demo launched - watch them {outcome} on impact"

    def add_random_body(self):
        viz = self.viz
        limit = viz.view_radius_au * AU
        anchor = max(viz.sim.bodies, key=lambda b: b.mass, default=None)
        origin = anchor.position if anchor is not None else Vector3D(0, 0, 0)
        position = Vector3D(origin.x + random.uniform(-limit, limit),
                             origin.y + random.uniform(-limit, limit), origin.z)

        velocity = Vector3D(0, 0, 0)
        if anchor is not None and anchor.position.distance_to(position) > 0:
            radius_vec = position - anchor.position
            r = radius_vec.magnitude()
            speed = (G * anchor.mass / r) ** 0.5
            tangent = Vector3D(-radius_vec.y, radius_vec.x, 0).normalized()
            velocity = anchor.velocity + tangent * speed

        mass = 5e23
        new_body = Planet(f"P{len(viz.sim.bodies)}", mass, CelestialBody.radius_from_mass(mass),
                           position, velocity, color="#9fb8c9", has_ring=True)
        viz.sim.add_body(new_body)
        viz.status_text = f"Added {new_body.name}"

    def reset_view(self):
        viz = self.viz
        viz.camera.reset_view()
        anchor = max(viz.sim.bodies, key=lambda b: b.mass, default=None)
        if anchor is not None:
            viz.camera.set_focus(anchor.position.x, anchor.position.y, anchor.position.z)
        else:
            viz.camera.set_focus(0.0, 0.0, 0.0)
        viz.status_text = "View reset"

    def handle_held_keys(self):
        viz = self.viz
        keys = pygame.key.get_pressed()
        if keys[pygame.K_UP]:
            viz.camera.adjust_pitch(1.2)
        if keys[pygame.K_DOWN]:
            viz.camera.adjust_pitch(-1.2)
        if keys[pygame.K_LEFT]:
            viz.camera.adjust_yaw(-1.5)
        if keys[pygame.K_RIGHT]:
            viz.camera.adjust_yaw(1.5)
        if keys[pygame.K_EQUALS] or keys[pygame.K_KP_PLUS]:
            viz.camera.adjust_zoom(1.03)
        if keys[pygame.K_MINUS] or keys[pygame.K_KP_MINUS]:
            viz.camera.adjust_zoom(1 / 1.03)
