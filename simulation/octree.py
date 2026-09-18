"""
octree.py

Barnes-Hut approximation for N-body gravity..
"""
from vector import Vector3D
from constants import G


class OctreeNode:
    """A cubic region of space that can hold one body or 8"""

    def __init__(self, center: Vector3D, half_size: float):
        self.center = center
        self.half_size = half_size
        self.mass = 0.0
        self.center_of_mass = Vector3D(0, 0, 0)
        self.body = None          
        self.children = None      

    @property
    def is_leaf(self):
        return self.children is None

    def _octant_index(self, position: Vector3D):
        index = 0
        if position.x >= self.center.x:
            index |= 1
        if position.y >= self.center.y:
            index |= 2
        if position.z >= self.center.z:
            index |= 4
        return index

    def _child_center(self, index):
        offset = self.half_size / 2
        dx = offset if index & 1 else -offset
        dy = offset if index & 2 else -offset
        dz = offset if index & 4 else -offset
        return Vector3D(self.center.x + dx, self.center.y + dy, self.center.z + dz)

    def _subdivide(self):
        self.children = [
            OctreeNode(self._child_center(i), self.half_size / 2) for i in range(8)
        ]

    def insert(self, new_body):
        if self.mass == 0 and self.body is None and self.is_leaf:
            self.body = new_body
            self.mass = new_body.mass
            self.center_of_mass = new_body.position
            return

        if self.is_leaf and self.body is not None:
            existing_body = self.body
            self.body = None
            self._subdivide()
            self.children[self._octant_index(existing_body.position)].insert(existing_body)

       
        self.children[self._octant_index(new_body.position)].insert(new_body)
        total_mass = self.mass + new_body.mass
        self.center_of_mass = (self.center_of_mass * self.mass +
                                new_body.position * new_body.mass) / total_mass
        self.mass = total_mass

    def compute_force_on(self, target, theta=0.5):
        """Net gravitational force this node's contents exert on target."""
        if self.mass == 0:
            return Vector3D(0, 0, 0)

        if self.is_leaf:
            if self.body is target:
                return Vector3D(0, 0, 0)
            return self._force_from_point(target, self.center_of_mass, self.mass)

        distance = target.position.distance_to(self.center_of_mass)
        width = self.half_size * 2
        if distance > 0 and (width / distance) < theta:
           
            return self._force_from_point(target, self.center_of_mass, self.mass)

       
        total = Vector3D(0, 0, 0)
        for child in self.children:
            total = total + child.compute_force_on(target, theta)
        return total

    @staticmethod
    def _force_from_point(target, point_position: Vector3D, point_mass: float):
        direction = point_position - target.position
        distance = direction.magnitude()
        if distance == 0:
            return Vector3D(0, 0, 0)
        magnitude = G * target.mass * point_mass / distance**2
        return direction.normalized() * magnitude


class Octree:
    

    def __init__(self, bodies, padding=1.5):
        self.root = self._build_root(bodies, padding)
        for body in bodies:
            self.root.insert(body)

    @staticmethod
    def _build_root(bodies, padding):
        if not bodies:
            return OctreeNode(Vector3D(0, 0, 0), 1.0)
        xs = [b.position.x for b in bodies]
        ys = [b.position.y for b in bodies]
        zs = [b.position.z for b in bodies]
        center = Vector3D((max(xs) + min(xs)) / 2,
                           (max(ys) + min(ys)) / 2,
                           (max(zs) + min(zs)) / 2)
        span = max(max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs), 1.0)
        return OctreeNode(center, span * padding / 2)

    def force_on(self, body, theta=0.5):
        return self.root.compute_force_on(body, theta)
