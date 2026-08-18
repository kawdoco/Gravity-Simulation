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
    """Abstract base class for any object in the simulation. Can't be
    instantiated directly - CelestialBody(...) raises a TypeError,
    because marker_size() below has no implementation here. Only a
    subclass that provides one (Planet, Star) can actually be built."""

    def __init__(self, name, mass, radius, position: Vector3D,
                 velocity: Vector3D, color="white"):
        self.name = name
        self._mass = mass  
        self.radius = radius
        self.position = position
        self.velocity = velocity
        self.color = color
        self.trail = []  # history of past positions, used to draw the orbit path

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
        """Every concrete body must say how big it renders. No default
        here on purpose - it forces each subclass to make its own
        decision instead of silently inheriting one that might not fit."""
        raise NotImplementedError

    @staticmethod
    def radius_from_mass(mass, density=3000.0):
        """Estimate a physically-plausible radius from mass, assuming a
        uniform density (kg/m^3). A staticmethod because it doesn't
        touch self or cls - it's just a formula that happens to live
        on this class because it's about bodies. Call it as
        CelestialBody.radius_from_mass(mass), no instance needed."""
        volume = mass / density
        return (3 * volume / (4 * 3.141592653589793)) ** (1 / 3)

    # ---- JSON serialization -----------------------------------------
    def to_dict(self):
        return {
            "type": self.__class__.__name__,
            "name": self.name,
            "mass": self._mass,
            "radius": self.radius,
            "position": list(self.position.as_tuple()),
            "velocity": list(self.velocity.as_tuple()),
            "color": self.color,
        }

    @classmethod
    def from_dict(cls, data):
        """Factory that rebuilds the correct subclass from saved data."""
        body_cls = BODY_CLASSES[data["type"]]
        return body_cls(
            name=data["name"],
            mass=data["mass"],
            radius=data["radius"],
            position=Vector3D(*data["position"]),
            velocity=Vector3D(*data["velocity"]),
            color=data.get("color", "white"),
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
