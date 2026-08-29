"""
integrator.py

 Different ways to advance every body's position and
velocity forward in time, given a function that computes the net
force on each body.

"""
from abc import ABC, abstractmethod


class Integrator(ABC):
    """Abstract base class  defines the interface every integrator
    must follow. """

    @abstractmethod
    def step(self, bodies, compute_forces, dt):
        raise NotImplementedError


class EulerIntegrator(Integrator):
    """Semi implicit Euler:  so orbits gradually change shape."""

    def step(self, bodies, compute_forces, dt):  # method overriding
        forces = compute_forces(bodies)
        for body in bodies:
            body.apply_force(forces[body], dt)          # v += (F/m)*dt
            body.position = body.position + body.velocity * dt
            body.record_trail()


class VerletIntegrator(Integrator):
    """Velocity Verlet: uses the acceleration at BOTH the start and the
    end of the step to update velocity

        x(t+dt) = x(t) + v(t)*dt + 1/2 * a(t) * dt^2
        v(t+dt) = v(t) + 1/2 * (a(t) + a(t+dt)) * dt
    """

    def step(self, bodies, compute_forces, dt):  # method overriding
        forces_start = compute_forces(bodies)
        accel_start = {body: forces_start[body] / body.mass for body in bodies}

        for body in bodies:
            body.position = (body.position + body.velocity * dt
                              + accel_start[body] * (0.5 * dt * dt))

        forces_end = compute_forces(bodies)
        for body in bodies:
            accel_end = forces_end[body] / body.mass
            body.velocity = body.velocity + (accel_start[body] + accel_end) * (0.5 * dt)
            body.record_trail()
