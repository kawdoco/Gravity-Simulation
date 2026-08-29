"""
vector.py

A minimal 3D vector class used for position, velocity, and force
throughout the simulation. Wrapping x, y, z in a class.
"""
import math


class Vector3D:
    """A simple 3D vector supporting the arithmetic the physics needs."""

    def __init__(self, x=0.0, y=0.0, z=0.0):
        self.x = x
        self.y = y
        self.z = z

    def __add__(self, other):
        return Vector3D(self.x + other.x, self.y + other.y, self.z + other.z)

    def __sub__(self, other):
        return Vector3D(self.x - other.x, self.y - other.y, self.z - other.z)

    def __mul__(self, scalar):
        return Vector3D(self.x * scalar, self.y * scalar, self.z * scalar)

    __rmul__ = __mul__  # "scalar * vector" works too

    def __truediv__(self, scalar):
        return Vector3D(self.x / scalar, self.y / scalar, self.z / scalar)

    def dot(self, other):
        return self.x * other.x + self.y * other.y + self.z * other.z

    def magnitude(self):
        return math.sqrt(self.x**2 + self.y**2 + self.z**2)

    def distance_to(self, other):
        return (self - other).magnitude()

    def normalized(self):
        mag = self.magnitude()
        if mag == 0:
            return Vector3D(0, 0, 0)
        return self / mag

    def as_tuple(self):
        return (self.x, self.y, self.z)

    def __repr__(self):
        return f"Vector3D({self.x:.3e}, {self.y:.3e}, {self.z:.3e})"
