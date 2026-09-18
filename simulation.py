
import json
from functools import singledispatchmethod

from vector import Vector3D
from body import CelestialBody
from octree import Octree
from integrator import VerletIntegrator
from constants import G


class Simulation:
    def __init__(self, use_barnes_hut=False, theta=0.5, restitution=0.0,
                 barnes_hut_threshold=450, integrator=None):
        self.bodies = []
        self.use_barnes_hut = use_barnes_hut       # switch between O(n^2) and Barnes-Hut
        self.theta = theta                         # Barnes-Hut accuracy/speed
        self.restitution = restitution
        self.barnes_hut_threshold = barnes_hut_threshold
        self.integrator = integrator or VerletIntegrator()

    @singledispatchmethod  # Polymorphism
    def add_body(self, body):
        self.bodies.append(body)

    @add_body.register  # Polymorphism
    def _(self, bodies: list):
        for body in bodies:
            self.bodies.append(body)

    def remove_body(self, body):
        if body in self.bodies:
            self.bodies.remove(body)

    def apply_drift(self, drift_velocity):
        """Adds one shared velocity to every body - used for "spiral"
        mode. Doesn't affect the orbits (gravity only cares about
        relative motion)."""
        for body in self.bodies:
            body.velocity = body.velocity + drift_velocity

    def _compute_forces(self, bodies):
        if self.use_barnes_hut and len(bodies) > self.barnes_hut_threshold:
            return self._barnes_hut_forces()
        return self._direct_forces()

    def _direct_forces(self):
        net_forces = {body: Vector3D(0, 0, 0) for body in self.bodies}
        for i, body_a in enumerate(self.bodies):
            for body_b in self.bodies[i + 1:]:
                direction = body_b.position - body_a.position
                distance = direction.magnitude()
                if distance == 0:
                    continue
                magnitude = G * body_a.mass * body_b.mass / distance**2
                force = direction.normalized() * magnitude
                net_forces[body_a] = net_forces[body_a] + force
                net_forces[body_b] = net_forces[body_b] - force  # Newton's third law
        return net_forces

    def _barnes_hut_forces(self):
        tree = Octree(self.bodies)
        return {body: tree.force_on(body, self.theta) for body in self.bodies}

    def _handle_collisions(self):
        i = 0
        while i < len(self.bodies):
            merged = False
            j = i + 1
            while j < len(self.bodies):
                a, b = self.bodies[i], self.bodies[j]
                if a.is_colliding(b):
                    if self.restitution <= 0:
                        self._merge(a, b)
                        merged = True
                        break
                    else:
                        self._bounce(a, b)
                j += 1
            if not merged:
                i += 1

    def _merge(self, a, b):
        total_mass = a.mass + b.mass
        merged_velocity = (a.velocity * a.mass + b.velocity * b.mass) / total_mass
        merged_position = (a.position * a.mass + b.position * b.mass) / total_mass
        merged_radius = (a.radius**3 + b.radius**3) ** (1 / 3)  # conserves volume
        bigger = a if a.mass >= b.mass else b

        bigger.mass = total_mass
        bigger.position = merged_position
        bigger.velocity = merged_velocity
        bigger.radius = merged_radius

        self.remove_body(a if bigger is b else b)

    def _bounce(self, a, b):
        normal = (b.position - a.position).normalized()
        relative_velocity = a.velocity - b.velocity
        velocity_along_normal = relative_velocity.dot(normal)
        if velocity_along_normal > 0:
            return

        impulse = -(1 + self.restitution) * velocity_along_normal
        impulse /= (1 / a.mass + 1 / b.mass)

        a.velocity = a.velocity + normal * (impulse / a.mass)
        b.velocity = b.velocity - normal * (impulse / b.mass)

    def step(self, dt):
        self.integrator.step(self.bodies, self._compute_forces, dt)  # Polymorphism
        self._handle_collisions()

    def save_state(self, path):
        data = [body.to_dict() for body in self.bodies]
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    def load_state(self, path):
        with open(path) as f:
            data = json.load(f)
        self.bodies = [CelestialBody.from_dict(entry) for entry in data]
