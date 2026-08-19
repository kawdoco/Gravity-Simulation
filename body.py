"""
body.py

Defines the class hierarchy for anything with mass that moves under
gravity. CelestialBody holds everything shared between bodies;
Planet and Star specialise it. Every body can be treated identically
by Simulation/Visualizer/Octree, but each renders and serialises
itself according to its own type (polymorphism).
"""
from abc import ABC, abstractmethod

from vector import Vector3D


class CelestialBody(ABC):
    """Abstract base class for any object in the simulation."""

    def __init__(self, name, mass, radius, position: Vector3D,
                 velocity: Vector3D, color="white", has_ring=False):
        self.name = name
        self._mass = mass  
        self.radius = radius
        self.position = position
        self.velocity = velocity
        self.color = color
        self.has_ring = has_ring 
        self.trail = []  # history of past positions,

    @property
    def mass(self):
        return self._mass

    @mass.setter
    def mass(self, value):
        if value <= 0:
            raise ValueError("Mass must be positive.")
        self._mass = value

    def apply_force(self, force: Vector3D, dt: float):
        """Update velocity from a net force using a = F / m, v += a * dt.
        Used by EulerIntegrator (see integrator.py)."""
        acceleration = force / self._mass
        self.velocity = self.velocity + acceleration * dt

    def record_trail(self, max_trail_length: int = 150):
        self.trail.append(self.position.as_tuple())
        if len(self.trail) > max_trail_length:
            self.trail.pop(0)

    def is_colliding(self, other):
        return self.position.distance_to(other.position) <= (self.radius + other.radius)

    @abstractmethod
    def marker_size(self):
        raise NotImplementedError

    @staticmethod
    def radius_from_mass(mass, density=3000.0):
        """Estimate a physically-plausible radius from mass, assuming a
        uniform density """
        volume = mass / density
        return (3 * volume / (4 * 3.141592653589793)) ** (1 / 3)

    # ---- JSON (de)serialization -----------------------------------------
    def to_dict(self):
        return {
            "type": self.__class__.__name__,
            "name": self.name,
            "mass": self._mass,
            "radius": self.radius,
            "position": list(self.position.as_tuple()),
            "velocity": list(self.velocity.as_tuple()),
            "color": self.color,
            "has_ring": self.has_ring,
        }

    @classmethod
    def from_dict(cls, data):
        """rebuilds the correct subclass from saved data."""
        body_cls = BODY_CLASSES[data["type"]]
        return body_cls(
            name=data["name"],
            mass=data["mass"],
            radius=data["radius"],
            position=Vector3D(*data["position"]),
            velocity=Vector3D(*data["velocity"]),
            color=data.get("color", "white"),
            has_ring=data.get("has_ring", False),
        )

    def __repr__(self):
        return f"{self.__class__.__name__}({self.name}, mass={self._mass:.2e} kg)"


class Planet(CelestialBody):
    """A planet - renders smaller than a star."""

    def marker_size(self):  # method overriding: fulfils the abstract contract above
        return 40


class Star(CelestialBody):
    """A star - renders larger, typically far more massive than planets."""

    def marker_size(self):  # method overriding: a different render size for stars
        return 200



BODY_CLASSES = {
    "Planet": Planet,
    "Star": Star,
}
