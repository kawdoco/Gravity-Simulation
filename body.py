"""body.py - class hierarchy for anything with mass that moves under gravity."""
from abc import ABC, abstractmethod

from vector import Vector3D


class CelestialBody(ABC):  # Abstraction

    def __init__(self, name, mass, radius, position: Vector3D,
                 velocity: Vector3D, color="white", has_ring=False):
        self.name = name
        self._mass = mass  # Encapsulation
        self.radius = radius
        self.position = position
        self.velocity = velocity
        self.color = color
        self.has_ring = has_ring
        self.trail = []

    @property  # Encapsulation
    def mass(self):
        return self._mass

    @mass.setter  # Encapsulation
    def mass(self, value):
        if value <= 0:
            raise ValueError("Mass must be positive.")
        self._mass = value

    def apply_force(self, force: Vector3D, dt: float):
        """v += (F/m)*dt"""
        acceleration = force / self._mass
        self.velocity = self.velocity + acceleration * dt

    def record_trail(self, max_trail_length: int = 900):
        self.trail.append(self.position.as_tuple())
        if len(self.trail) > max_trail_length:
            self.trail.pop(0)

    def is_colliding(self, other):
        return self.position.distance_to(other.position) <= (self.radius + other.radius)

    @abstractmethod  # Abstraction
    def marker_size(self):
        raise NotImplementedError

    @staticmethod  # Static Method
    def radius_from_mass(mass, density=3000.0):
        volume = mass / density
        return (3 * volume / (4 * 3.141592653589793)) ** (1 / 3)

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


class Planet(CelestialBody):  # Inheritance
    def marker_size(self):  # Polymorphism
        return 40


class Star(CelestialBody):  # Inheritance
    def marker_size(self):  # Polymorphism
        return 200


BODY_CLASSES = {
    "Planet": Planet,
    "Star": Star,
}
