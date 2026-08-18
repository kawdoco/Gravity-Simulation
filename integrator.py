"""
integrator.py

Strategy pattern: different ways to advance every body's position and
velocity forward in time, given a function that computes the net
force on each body. Simulation holds ONE Integrator and delegates all


This mirrors the reference project's use of Verlet integration, just
implemented as its own class 
"""
from abc import ABC, abstractmethod


class Integrator(ABC):
    """Abstract base class - defines the interface every integrator
    must follow. Integrator(...) can't be instantiated directly (it
    would raise a TypeError); only a subclass that implements step()
    can be built. Simulation only ever calls .step(), and doesn't
    care which subclass it's holding (polymorphism)."""

    @abstractmethod
    def step(self, bodies, compute_forces, dt):
        raise NotImplementedError


class EulerIntegrator(Integrator):
    """Semi-implicit ("symplectic") Euler: update velocity first using
    the current force, then use that NEW velocity to update position.
    One force calculation per step - cheap, but energy slowly drifts
    over long runs, so orbits gradually change shape."""

    def step(self, bodies, compute_forces, dt):  # method overriding
        forces = compute_forces(bodies)
        for body in bodies:
            body.apply_force(forces[body], dt)          # v += (F/m)*dt
            body.position = body.position + body.velocity * dt
            body.record_trail()


class VerletIntegrator(Integrator):
    """Velocity Verlet: uses the acceleration at BOTH the start and the
    end of the step to update velocity, instead of just the start.
    That symmetry is what makes it "symplectic" - it conserves energy
    far better over long runs than plain Euler. Costs a second force
    calculation per step, which is the price for that accuracy.

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
